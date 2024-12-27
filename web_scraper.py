import requests  
from bs4 import BeautifulSoup  
import spacy 
import json
import re


nlp = spacy.load("en_core_web_sm")
def scrape_and_extract(website_url, country_address, roles):
    try:

        response = requests.get(website_url)
        if response.status_code != 200:
            print(f"Failed to fetch {website_url}. Status code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("meta", property="og:title")
        date_tag = soup.find("meta", property="article:published_time")

        content_div = soup.find("div", class_="td-post-content") 
        paragraphs = content_div.find_all("p") if content_div else []

        data_entry = {
            "title": title_tag["content"] if title_tag else None,
            "date": date_tag["content"] if date_tag else None,
            "funding_amount": None,
            "ceo_cto_cfo": [],
            "country_address": country_address,
            "fund_name": None,
            "fund_size": None,
            "investor_composition": {},
            "focus_sectors": [],
            "focus_regions": [],
        }

        # Extract relevant data
        for paragraph in paragraphs:
            paragraph_text = paragraph.get_text(strip=True)
            doc = nlp(paragraph_text)
            
            funding_match = re.search(r"(€|EUR|£|\$)\s?(\d+[\.]?\d*)\s?(M|Billion|K)?", paragraph_text, re.IGNORECASE)
            if funding_match:
                funding_amount = funding_match.group(0).strip()
                # print(f"Funding amount found: {funding_amount}")  
                data_entry["funding_amount"] = funding_amount

            for ent in doc.ents:
                if ent.label_ == "GPE":
                    if not data_entry["country_address"].get("country"):
                        data_entry["country_address"]["country"] = ent.text
                        # print(f"Country extracted: {ent.text}")  
                    if "," in ent.text: 
                        city_state = ent.text.split(",")
                        if len(city_state) > 1:
                            data_entry["country_address"]["city"] = city_state[0].strip()
                            data_entry["country_address"]["state"] = city_state[1].strip()
                        # print(f"City: {data_entry['country_address']['city']}, State: {data_entry['country_address']['state']}")  # Debug

            for ent in doc.ents:
                if ent.label_ == "PERSON" and any(role.lower() in paragraph_text.lower() for role in roles):
                    data_entry["ceo_cto_cfo"].append(ent.text)

            if "led by" in paragraph_text.lower() or "under the leadership of" in paragraph_text.lower():
                try:
                    parts = paragraph_text.lower().split("led by")
                    if len(parts) > 1:
                        ceo_name = parts[1].split(",")[0].strip()
                        data_entry["ceo_cto_cfo"].append(ceo_name)
                except Exception as e:
                    print(f"Error while extracting CEO name: {e}")

            if "closed" in paragraph_text.lower() and "EUR" in paragraph_text:
                try:
                    parts = paragraph_text.split("at")
                    if len(parts) > 1:
                        data_entry["fund_name"] = parts[0].split(",")[0].strip()
                        data_entry["fund_size"] = parts[1].split("EUR")[1].strip()
                except IndexError:
                    print("Error while extracting fund name and size. Skipping this paragraph.")

            if "investor base" in paragraph_text.lower():
                try:
                    investors = paragraph_text.split(":")[1].split(";")
                    for investor in investors:
                        key, value = investor.split("(")
                        data_entry["investor_composition"][key.strip()] = value.strip(")%")
                except (IndexError, ValueError):
                    print("Error while extracting investor composition. Skipping this paragraph.")

            if "focus sectors" in paragraph_text.lower():
                try:
                    data_entry["focus_sectors"] = [
                        sector.strip() for sector in paragraph_text.split("Focus sectors are")[1].split(",")
                    ]
                except IndexError:
                    print("Error while extracting focus sectors. Skipping this paragraph.")

            if "key regions" in paragraph_text.lower():
                try:
                    data_entry["focus_regions"] = [
                        region.strip() for region in paragraph_text.split("Key regions are")[1].split("and")
                    ]
                except IndexError:
                    print("Error while extracting focus regions. Skipping this paragraph.")

        with open("extracted_data.json", "w") as json_file:
            json.dump(data_entry, json_file, indent=4)

        print("Data successfully extracted and saved to 'extracted_data.json'.")
        

    except Exception as e:
        print(f"An error occurred: {e}")


website_url = "https://www.finsmes.com/2024/12/xerox-to-acquire-lexmark.html"
country_address = {"city": "", "state": "", "country": ""}

roles = ["CEO", "CTO", "CFO"]

scrape_and_extract(website_url, country_address, roles)
