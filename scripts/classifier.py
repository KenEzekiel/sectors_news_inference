import dotenv
dotenv.load_dotenv()

import json
from supabase import create_client, Client
import os
from datetime import datetime
from openai import OpenAI
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string

from llama_index.llms.groq import Groq
# from sklearn.metrics.pairwise import cosine_similarity
# from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_groq import ChatGroq
# from langchain.agents import create_tool_calling_agent, AgentExecutor

SUBSECTOR_LOAD = True
TAG_LOAD = True

# PREPARATION
nltk.data.path.append('./nltk_data')


SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(os.getenv("SUPABASE_URL"), SUPABASE_KEY)
client = OpenAI(
  api_key=os.getenv('OPENAI_API_KEY'),  
)
llm = Groq(
    model="llama3-70b-8192",
    api_key=os.getenv('GROQ_API_KEY'),
)

# DATA LOADING
# Subsectors data
def load_subsector_data():
  if datetime.today().day in [1, 15]:
    response = supabase.table('idx_subsector_metadata').select('slug, description').execute()
    
    subsectors = {}

    for row in response.data:
      subsectors[row['slug']] = row['description']
    with open('./data/subsectors_data.json', 'w') as f:
      f.write(json.dumps(subsectors))
    
    return subsectors
  else:
    with open('./data/subsectors_data.json', 'r') as f:
      subsectors = json.load(f)
    return subsectors
# Tags data
def load_tag_data():
  tags = [
    # Economy
    "Macroeconomics", "Inflation", "Interest Rates", "GDP", "Unemployment",
    
    # Stock Market
    "IDX Composite", "LQ45", "Market Trends", "Market Sentiment", "Stock Indexes", "BEI",
    
    # Commodities
    "Palm Oil", "Coal", "Gold", "Oil", "Agricultural Commodities",
    
    # Currencies
    "IDR", "USD", "Forex", "Cryptocurrency",
    
    # Company News
    "Earnings Report", "Quarterly Results", "Revenue", "Profit Margins",
    "Mergers and Acquisitions", "IPO", "Stock Splits", "Dividends",
    "CEO", "Executive Changes", "Board of Directors",
    "Lawsuits", "Regulations", "Compliance",
    
    # Sector-specific News
    "Tech Stocks", "Innovation", "Startups",
    "Banks", "Investment Firms", "Insurance", "Fintech",
    "Oil & Gas", "Renewable Energy", "Utilities", "Energy Stocks",
    "Retail", "Food & Beverage", "Apparel",
    
    # Market Analysis
    "Technical Analysis", "Chart Patterns", "Indicators", "Moving Averages",
    "Fundamental Analysis", "Valuation", "Financial Ratios", "Balance Sheets",
    "Bullish", "Bearish", "Neutral",
    "Day Trading", "Swing Trading", "Long-term Investing",
    
    # Events and Reports
    "Economic Reports", "Retail Sales", "Product Launches", "Conferences",
    
    # Investor Insights
    "Analyst Ratings", "Buy", "Hold", "Sell", "Target Price",
    "Bullish", "Bearish",
    
    # Global News
    "Asian Markets", "Emerging Markets",
    
    # Miscellaneous
    "ESG", "Green Energy", "Corporate Responsibility",
    
    # Technology Trends
    "AI", "Blockchain", "Cybersecurity"
  ]
  return tags

# Ticker and Company name data, renew in date 1, 15 from supabase
def load_company_data():
  if datetime.today().day in [1, 15]:
    response = supabase.table('idx_company_report').select('symbol, company_name, sub_sector').execute()

    company = {}

    for row in response.data:
      company[row['symbol']] = {
        "symbol": row['symbol'],
        "name": row['company_name'],
        "sub_sector": row['sub_sector']
      }
    
    with open('./data/companies.json', 'w') as f:
      f.write(json.dumps(company))
    return company
  else:
    with open('./data/companies.json', 'r') as f:
      company = json.loads(f.read())
    return company

# CLASSIFICATION
# @Private method
def classify_ai(body, category):
  tags = load_tag_data()
  company = load_company_data()
  subsectors = load_subsector_data()
  prompt = {
    "tags": f"Tags: {','.join(tag for tag in tags)} and article: {body}. Identify 5 most relevant tags to the article, in the format: [tag1, tag2, etc].",
    "tickers": f"Tickers: {','.join(ticker for ticker in company.keys())} and article: {body}. Identify all the tickers in the article, in the format [ticker1, ticker2, etc].",
    "subsectors": f"subsectors: {','.join(subsector for subsector in subsectors.keys())} and article: {body}. Identify the subsector of the article, in the format of subsector-name.",
    "sentiment": f"Classify the sentiment of the article ('bullish' or 'bearish'). Article: {body}. \n Answer in one word (bullish or bearish)"
  }

  response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that classifies characteristics of a news article (tags, subsectors, tickers)."},
            {"role": "user", "content": prompt[category]}
        ],
        max_tokens=150,
        temperature=0.5
    )
  return response.choices[0].message.content

def classify_llama(body, category):
  tags = load_tag_data()
  company = load_company_data()
  subsectors = load_subsector_data()
  prompt = {
        "tags": f"Tags: {', '.join(tag for tag in tags)} and article: {body}. Identify 5 most relevant tags to the article, only answer in the format: [tag1, tag2, etc] and nothing else.",
        "tickers": f"Tickers: {', '.join(ticker for ticker in company.keys())} and article: {body}. Identify all the tickers in the article, only answer in the format [ticker1, ticker2, etc] and nothing else.",
        "subsectors": f"Subsectors: {', '.join(subsector for subsector in subsectors.keys())} and article: {body}. Identify the subsector of the article, only answer in the format of subsector-name and nothing else.",
        "sentiment": f"Classify the sentiment of the article ('bullish' or 'bearish'). Article: {body}. Answer in one word (bullish or bearish)."
  }

  outputs = llm.complete(prompt[category])

  return outputs  

# @Private method
def identify_company_names(body):
  prompt = f"Identify all the company names mentioned in the following article:\n\n{body}\n\n For each company, for example PT. Antara Business Service (ABS), write it as Antara Business Service only\n\nOnly answer in the format: A, B, etc.\n\n Say nothing else."

  response = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=[
          {"role": "system", "content": "You are a helpful assistant that classifies characteristics of a news article (tags, subsectors, tickers)."},
          {"role": "user", "content": prompt}
      ],
      max_tokens=150,
      temperature=0.5,
      stop=None,
      n=1
  )
  
  company_names = response.choices[0].message.content.strip().split(',')
  company_names_list = [name.strip() for name in company_names if name.strip()]
  company_names = str(llm.complete(prompt)).split(',')
  print(company_names)
  for name in company_names:
    if name not in company_names_list:
      company_names_list.append(name)
  return company_names_list

# @Private method
def match_ticker_codes(company_names, company_data):
  matched_tickers = []
  for name in company_names:
    for ticker, info in company_data.items():
      if name.lower() in info['name'].lower() or name.lower() in ticker.lower():
        if ticker not in matched_tickers:
          matched_tickers.append(ticker)
  return matched_tickers

# @Private method
def preprocess_text(text):
    # Tokenize the text into words
    tokens = word_tokenize(text)
    
    # Convert to lowercase
    tokens = [word.lower() for word in tokens]
    
    # Remove punctuation
    table = str.maketrans('', '', string.punctuation)
    tokens = [word.translate(table) for word in tokens]
    
    # Remove non-alphabetic tokens
    tokens = [word for word in tokens if word.isalpha()]
    
    # Remove stop words
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]
    
    # Lemmatize the words
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    
    # Join the tokens back into a single string
    processed_text = ' '.join(tokens)
    
    return processed_text

# @Private method
def get_embedding(text):
  response = client.embeddings.create(
      model="text-embedding-ada-002",
      input=text
  )
  return response.data[0].embedding

# EMBEDDINGS LOAD
def load_subsector_embeddings():
  if SUBSECTOR_LOAD:
    with open('./data/subsector_embeddings.json', 'r') as f:
      subsector_embeddings = json.load(f)
  else:
    subsectors = load_subsector_data()
    subsector_embeddings = {subsector: get_embedding(description) for subsector, description in subsectors.items()}
    with open('./data/subsector_embeddings.json', 'w') as f:
      json.dump(subsector_embeddings, f)
  return subsector_embeddings

def load_tag_embeddings():
  if TAG_LOAD: 
    with open('./data/tag_embeddings.json', 'r') as f:
      tag_embeddings = json.load(f)
  else:
    # RENEW IF TAGS CHANGE
    tags = load_tag_data()
    tag_embeddings = {tag: get_embedding(tag) for tag in tags}
    with open('./data/tag_embeddings.json', 'w') as f:
      json.dump(tag_embeddings, f)
  return tag_embeddings

# @Public method
def get_tickers(text):
  company_names = identify_company_names(text)
  company = load_company_data()
  return match_ticker_codes(company_names, company)

# @Public method
def get_tags_chat(text):
  text = preprocess_text(text)
  # return classify_ai(text, "tags")
  return classify_llama(text, "tags")

# @Public method
def get_subsector_chat(text):
  text = preprocess_text(text)
  # return classify_ai(text, "subsectors")
  return classify_llama(text, "subsectors")

# @Public method
def get_sentiment_chat(text):
  text = preprocess_text(text)
  
  # return classify_ai(text, "sentiment")
  return classify_llama(text, "sentiment")

# @Public method
# def get_tags_embeddings(text):
#   text = preprocess_text(text)
#   article_embedding = get_embedding(text)
#   tag_embeddings = load_tag_embeddings()
  
#   similarities = {tag: cosine_similarity([article_embedding], [embedding])[0][0] for tag, embedding in tag_embeddings.items()}

#   top_5_tags = sorted(similarities, key=similarities.get, reverse=True)[:5]

#   return top_5_tags
    
# @Public method
# def get_subsector_embeddings(text):
#   text = preprocess_text(text)
#   article_embedding = get_embedding(text)
#   subsector_embeddings = load_subsector_embeddings()
  
#   similarities_subsector = {subsector: cosine_similarity([article_embedding], [embedding])[0][0] for subsector, embedding in subsector_embeddings.items()}
  
#   most_relevant_subsector = max(similarities_subsector, key=similarities_subsector.get)
  
#   return most_relevant_subsector


# body = ["GoTo, a merger between Gojek and Tokopedia, has absorbed nearly 80% of its IPO funds, amounting to Rp10.76 trillion by the end of June 2024. The company has generated a net proceeds of Rp13.5 trillion during its IPO in 2022, leaving Rp2.81 trillion remaining for operational and strategic purposes, including investments in companies like Gopay and Velox Digital.",
# "PT. Bank Raya Indonesia Tbk has scheduled a share buyback with a budget of IDR 20 billion, pending approval from shareholders on August 21, 2024, aiming to increase employee engagement in the company without affecting business operations. The buyback will be funded from internal cash, and the number of shares to be repurchased has not been disclosed, projected to be below 10% of the issued paid-up capital.",
# "PT Bank Syariah Indonesia (BSI) has made it to the top 5 state-owned enterprises with the largest market capitalization in Indonesia, reaching Rp116 trillion in July 2024. BSI's success is attributed to its inclusive, modern, and digital approach, with positive financial performance including distributing Rp855.56 billion cash dividends in 2023 and achieving a Rp1.71 trillion profit in Q1 2024 driven by robust growth in third-party funds and mobile banking transactions.",
# "Hary Tanoesoedibjo has rescued MNC Asia Holding by acquiring 26 million shares at Rp50 each, investing a total of Rp1.3 billion. Following the purchase, Tanoesoedibjo's portfolio now holds 2.59 billion shares, a 3.1% increase from before the transaction.",
# "Stocks in LQ45 index like UNVR, MBMA, and SIDO dropped as the market rose. UNVR closed at Rp 2,800, down by 2.10%, with a total transaction value of Rp 43.30 billion and a P/E ratio of 18.82x. Similarly, MBMA saw a 2.29% decline, closing at Rp 640, and SIDO ended at Rp 725 per share, down by 2.03%."]

# for text in body:
#   print("TEXT:")
#   print(text)
#   print("CLASSIFIED TICKERS:")
#   print(get_tickers(text))
#   print("CLASSIFIED TAGS METHOD 1")
#   print(get_tags_chat(text))
#   print("CLASSIFIED SUBSECTOR METHOD 1")
#   print(get_subsector_chat(text))
#   # print("CLASSIFIED TAGS METHOD 2")
#   # print(get_tags_embeddings(text))
#   # print("CLASSIFIED SUBSECTOR METHOD 2")
#   # print(get_subsector_embeddings(text))
#   print("CLASSIFIED SENTIMENT")
#   print(get_sentiment_chat(text))
#   print("")
  
# Result
# Tickers belum konsisten
# tags method 1 kadang beda, method 2 selalu sama
# subsectors selalu sama di setiap method, walau antar method beda
# sentiment konsisten