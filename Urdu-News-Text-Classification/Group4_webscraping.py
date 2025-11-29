# %%
# !pip install BeautifulSoup
!pip install beautifulsoup4

# %%
import os
import json
import time
import random
import zipfile
import requests
import pandas as pd
from bs4 import BeautifulSoup

# %% [markdown]
# # Class Explanation: `NewsScraper`
# 
# ## Overview
# The `NewsScraper` class is designed for scraping news articles from three different Urdu news websites: Geo, Jang, and Express. The class has methods that cater to each site's unique structure and requirements. Below, we will go through the class and its methods, detailing what each function does, the input it takes, and the output it returns.
# 
# ## Class Definition
# 
# ```python
# class NewsScraper:
#     def __init__(self, id_=0):
#         self.id = id_
# ```
# 
# 
# ## Method 1: `get_express_articles`
# 
# ### Description
# Scrapes news articles from the Express website across categories like saqafat (entertainment), business, sports, science-technology, and world. The method navigates through multiple pages for each category to gather a more extensive dataset.
# 
# ### Input
# - **`max_pages`**: The number of pages to scrape for each category (default is 7).
# 
# ### Process
# - Iterates over each category and page.
# - Requests each category page and finds article cards within `<ul class='tedit-shortnews listing-page'>`.
# - Extracts the article's headline, link, and content by navigating through `<div class='horiz-news3-caption'>` and `<span class='story-text'>`.
# 
# ### Output
# - **Returns**: A tuple of:
#   - A Pandas DataFrame containing columns: `id`, `title`, and `link`).
#   - A dictionary `express_contents` where the key is the article ID and the value is the article content.
# 
# ### Data Structure
# - Article cards are identified by `<li>` tags.
# - Content is structured within `<span class='story-text'>` and `<p>` tags.
# 
# 

# %%
class NewsScraper:
    def __init__(self,id_=0):
        self.id = id_


  # write functions to scrape from other websites
    def get_geo_articles(self):
        geo_df = {
            "id": [],
            "title": [],
            "link": [],
            "content": [],
            "gold_label": [],
        }
        base_url = 'https://urdu.geo.tv/category/'
        categories = ['world', 'sports', 'entertainment', 'business', 'science-technology']
        num_pages = 2 

        for category in categories:
            print(f"Scraping articles from category '{category}'...")

            success_count = 0

            for page in range(1, num_pages + 1):
                print(f"  Scraping page {page} of '{category}'...")
                url = f"{base_url}{category}?page={page}"
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                cards = soup.find_all('div', class_='singleBlock')
                print(f"\t--> Found {len(cards)} articles on page {page} of '{category}'.")

                for card in cards:
                    try:
                        headline = card.find('h2').get_text(strip=True)

                        link = card.find('a', class_='open-section')['href']

                        article_response = requests.get(link)
                        article_response.raise_for_status()
                        content_soup = BeautifulSoup(article_response.text, "html.parser")

                        paras = content_soup.find_all('p')
                        combined_text = " ".join(
                            p.get_text(strip=True).replace('\xa0', ' ').replace('\u200b', '')
                            for p in paras if p.get_text(strip=True)
                        )

                        geo_df['id'].append(self.id)
                        geo_df['title'].append(headline)
                        geo_df['link'].append(link)
                        geo_df['gold_label'].append(category)
                        geo_df['content'].append(combined_text)

                        self.id += 1
                        success_count += 1

                    except Exception as e:
                        print(f"\t--> Failed to scrape an article on page {page} of '{category}': {e}")

            print(f"\t--> Successfully scraped {success_count} articles from '{category}'.\n")

        return pd.DataFrame(geo_df)

    def get_jang_articles(self):
        jang_df = {
            "id": [],
            "title": [],
            "link": [],
            "content": [],
            "gold_label": [],
        }
        base_url = 'https://jang.com.pk'
        categories = {
            'world': 'latest-news/world',
            'sports': 'latest-news/sports',
            'entertainment': 'latest-news/entertainment',
            'business': 'latest-news/business',
        }

        for category, path in categories.items():
            url = f"{base_url}/category/{path}"
            print(f"Scraping {category} articles from: {url}")
            
            try:
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                articles = soup.find_all('li')
                print(f"\t--> Found {len(articles)} articles in '{category}' category.")

                success_count = 0

                for article in articles:
                    try:
                        headline_tag = article.find('h2')
                        headline = headline_tag.get_text(strip=True) if headline_tag else None

                        link_tag = article.find('a', href=True)
                        link = link_tag['href'] if link_tag else None

                        if not headline or not link:
                            continue

                        if link and not link.startswith("http"):
                            link = f"{base_url}{link}"

                        article_response = requests.get(link)
                        article_response.raise_for_status()
                        article_soup = BeautifulSoup(article_response.text, "html.parser")

                        paras = article_soup.find_all('p')
                        combined_text = " ".join(
                            p.get_text(strip=True).replace('\xa0', ' ').replace('\u200b', '')
                            for p in paras if p.get_text(strip=True)
                        )

                        jang_df['id'].append(self.id)
                        jang_df['title'].append(headline)
                        jang_df['link'].append(link)
                        jang_df['gold_label'].append(category)
                        jang_df['content'].append(combined_text)

                        self.id += 1
                        success_count += 1

                    except Exception as e:
                        print(f"\t--> Failed to scrape an article in '{category}': {e}")

                print(f"\t--> Successfully scraped {success_count} articles from '{category}' category.\n")

            except Exception as e:
                print(f"Failed to retrieve category page for '{category}': {e}")
        
        return pd.DataFrame(jang_df)

    def get_dunya_articles(self, max_pages=7):
        dunya_df = {
            "id": [],
            "title": [],
            "link": [],
            "content": [],
            "gold_label": [],
        }

        base_url = 'https://urdu.dunyanews.tv'
        categories = ['Business', 'Sports', 'Entertainment', 'World', 'Technology']  # Add or update categories as needed

        for category in categories:
            print(f"Scraping articles from category '{category}'...")

            url = f"{base_url}/index.php/ur/{category}"
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            cards = soup.find_all('h3', class_='col-md-12 newsttl') + \
                    soup.find_all('div', class_='col-md-6 col-sm-6 col-xs-6') + \
                     soup.find_all('div', class_='col-md-8')


            print(f"\t--> Found {len(cards)} articles in '{category}'.")

            success_count = 0

            for card in cards:
                try:

                    if 'newsttl' in card.get('class', []):
                        title_tag = card.find('a')
                    else:
                        title_tag = card.find('h3').find('a')

                    title = title_tag.get_text(strip=True)
                    link_suffix = title_tag['href']
                    link = base_url + link_suffix if link_suffix.startswith('/') else link_suffix

                    article_response = requests.get(link)
                    article_response.raise_for_status()
                    content_soup = BeautifulSoup(article_response.text, "html.parser")

                    paras = content_soup.find('div', class_='main-news col-md-12').find_all('p')
                    combined_text = " ".join(
                        p.get_text(strip=True).replace('\xa0', ' ').replace('\u200b', '')
                        for p in paras if p.get_text(strip=True)
                    )

                    gold_label = category if category != 'Technology' else 'Science-Technology'

                    dunya_df['id'].append(self.id)
                    dunya_df['title'].append(title)
                    dunya_df['link'].append(link)
                    dunya_df['gold_label'].append(category)
                    dunya_df['content'].append(combined_text)

                    self.id += 1
                    success_count += 1

                except Exception as e:
                    print(f"\t--> Failed to scrape an article in '{category}': {e}")

            print(f"\t--> Successfully scraped {success_count} articles from '{category}'.\n")

        return pd.DataFrame(dunya_df)


    def get_express_articles(self, max_pages=7):
        express_df = {
            "id": [],
            "title": [],
            "link": [],
            "content": [],
            "gold_label": [],
        }
        base_url = 'https://www.express.pk'
        categories = ['saqafat', 'business', 'sports', 'science', 'world']   # saqafat is entertainment category

        # Iterating over the specified number of pages
        for category in categories:
            for page in range(1, max_pages + 1):
                print(f"Scraping page {page} of category '{category}'...")
                url = f"{base_url}/{category}/archives?page={page}"
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # Finding article cards
                cards = soup.find('ul', class_='tedit-shortnews listing-page').find_all('li')  # Adjust class as per actual site structure
                print(f"\t--> Found {len(cards)} articles on page {page} of '{category}'.")

                success_count = 0

                for card in cards:
                    try:
                        div = card.find('div',class_='horiz-news3-caption')

                        # Article Title
                        headline = div.find('a').get_text(strip=True).replace('\xa0', ' ')

                        # Article link
                        link = div.find('a')['href']

                        # Requesting the content from each article's link
                        article_response = requests.get(link)
                        article_response.raise_for_status()
                        content_soup = BeautifulSoup(article_response.text, "html.parser")


                        # Content arranged in paras inside <span> tags
                        paras = content_soup.find('span',class_='story-text').find_all('p')

                        combined_text = " ".join(
                        p.get_text(strip=True).replace('\xa0', ' ').replace('\u200b', '')
                        for p in paras if p.get_text(strip=True)
                        )

                        # Storing data
                        express_df['id'].append(self.id)
                        express_df['title'].append(headline)
                        express_df['link'].append(link)
                        express_df['gold_label'].append(category.replace('saqafat','entertainment').replace('science','science-technology'))
                        express_df['content'].append(combined_text)

                        # Increment ID and success count
                        self.id += 1
                        success_count += 1

                    except Exception as e:
                        print(f"\t--> Failed to scrape an article on page {page} of '{category}': {e}")

                print(f"\t--> Successfully scraped {success_count} articles from page {page} of '{category}'.")
            print('')

        return pd.DataFrame(express_df)

# %%
scraper = NewsScraper()

# %%
express_df = scraper.get_express_articles()

# %%
geo_df = scraper.get_geo_articles()

# %%
geo_df.shape[0]

# %%
geo_df.head()

# %%
geo_df.tail()

# %%
jang_df = scraper.get_jang_articles()

# %%
jang_df.head()

# %%
jang_df.shape[0]

# %%
jang_df.tail()

# %%
def drop_last_n_rows(df, n=4):
    return df.iloc[:-n] if len(df) > n else pd.DataFrame()

jang_df = jang_df.groupby('gold_label', group_keys=False).apply(drop_last_n_rows, n=4)

# had to remove last 4 rows for each category of the jang df as they were getting repeated for some reason


# %%
jang_df.shape[0]

# %%
business_articles = jang_df[jang_df['gold_label'] == 'sports']
print(business_articles)

# %%
express_df.shape[0]

# %%
dunya_df = scraper.get_dunya_articles()

# %%
dunya_df.shape[0]

# %%
dunya_df.head()

# %%
business_articles = dunya_df[dunya_df['gold_label'] == 'Sports']
(business_articles)

# %%
# EDA on dunya and geo content column(removed first 2 words as they contained cities of the news, not needed)
dunya_df['content'] = dunya_df['content'].str.replace(r'^([^\s]+\s+){2}', '', regex=True)
geo_df['content'] = geo_df['content'].str.replace(r'^([^\s]+\s+){2}', '', regex=True)


# print(dunya_df[['content']].head())

#combining the dataframe
combined_df = pd.concat([geo_df, jang_df, express_df, dunya_df], ignore_index=True)
# (combined_df.head())

#making all gold_labels lower case for consistency
combined_df['gold_label'] = combined_df['gold_label'].str.lower()
# combined_df.shape[0]

combined_df


# %%
geo_df['content'] = geo_df['content'].str.replace(r'^([^\s]+\s+){1}', '', regex=True)

# %%
#removing punctuation and numbers
import regex as re
def clean_text(x):
    return re.sub(r'[^\u0600-\u06FF\s]', '', x)

combined_df['content'] = combined_df['content'].apply(clean_text)

print(combined_df[['title', 'content']].head())

# %%
combined_df['gold_label'] = combined_df['gold_label'].replace('technology', 'science-technology')

# %%
combined_df.tail

# %%
combined_df = combined_df.drop(columns=['id'])

combined_df['id'] = range(len(combined_df))
cols = ['id'] + [col for col in combined_df.columns if col != 'id']

combined_df = combined_df[cols]

combined_df

# adding id for each article

# %%
combined_df['content'] = combined_df['content'].str.replace('،', '', regex=False)
#removing commas from here

# %% [markdown]
# # Output
# - Save a combined csv of all 3 sites.

# %%
combined_df.to_csv('output_file.csv', index=False, encoding='utf-8')

# %%



