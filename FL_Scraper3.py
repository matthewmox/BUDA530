import requests
from bs4 import BeautifulSoup
import pdfplumber
import pandas as pd
import csv
import os
from datetime import datetime, timedelta
import logging
import PyPDF2
import re

def get_table_text(pdf_filepath, counties_list):
    PdfReader = PyPDF2.PdfReader(pdf_filepath)

    num_pages = len(PdfReader.pages)
    text = ''
    for page_number in range(num_pages):
        page = PdfReader.pages[page_number]
        page_text = page.extract_text()
        text = text + page_text

    start_index = text.find("Arbovirus Activity by County") + 18
    end_index = text.find("Acknowledgements and Data Sources", start_index)

    relevant_section = text[start_index:end_index-1]

    lines = relevant_section.split("\n")
    lines = [x for x in lines if len(x) > 1]

    for line in lines:
        line_contents = line.split(" ")
        line_contents = [x for x in line_contents if len(x) > 0]

        for test_county in counties_list:
            if test_county in line_contents and line_contents.index(test_county) != 0:
                county_ind = line_contents.index(test_county)
                line_contents[county_ind-1] = '\n'
                lines[lines.index(line)] = " ".join(line_contents)

            elif " " in test_county:
                county_first_word = test_county.split(" ")[0]
                test_county = test_county.replace(" ", "")

                if test_county in str("".join(line_contents)):
                    if str("".join(line_contents)).startswith(test_county):
                        break
                    else:
                        county_ind = line_contents.index(county_first_word)
                        line_contents[county_ind-1] = '\n'
                        lines[lines.index(line)] = " ".join(line_contents)

    relevant_section = "\n".join(lines)

    return relevant_section


def create_dict(disease_cat_list):
    disease_cat_dict = dict.fromkeys(["county", "week"] + disease_cat_list)
    disease_cat_dict["WNV"] = {}
    disease_cat_dict["EEEV"] = {}
    disease_cat_dict["EEE"] = {}
    disease_cat_dict["SLEV"] = {}
    disease_cat_dict["Dengue"] = {}
    disease_cat_dict["Chikungunya"] = {}
    disease_cat_dict["HJV"] = {}
    disease_cat_dict["Malaria"] = {}

    return disease_cat_dict


def extract_arbovirus_activity(text):
    lines = text.split("\n")
    county = ""
    county_list = []
    activity_list = []
    for line in lines:
        line_contents = line.split(" ")

        if len(line_contents) > 1 and ":" not in line_contents[0] and "/" not in line_contents[0]:
            new_county = True
        else:
            new_county = False

        if new_county:
            if len(county) > 0:
                previous_county = county
                previous_info = activity_info
                county_list.append(previous_county)
                activity_list.append("".join(previous_info))

            diseases_present = [x for x in line_contents if ":" in x]

            if len(diseases_present) > 0:
                disease_list_start_ind = line_contents.index(diseases_present[0])
                county = "".join(line_contents[:disease_list_start_ind])
                activity_info = "".join(line_contents[disease_list_start_ind:])
            else:
                activity_info = ""

        else:
            activity_info = activity_info + "".join(line_contents)

    results = pd.DataFrame(list(zip(county_list, activity_list)), columns=['county', 'activity'])
    return results


def generate_counts_df(test_data, week, date):
    disease_cat_list = ["WNV", "EEEV", "SLEV", "Dengue", "Chikungunya", "HJV", "Malaria", "EEE"]
    disease_sub_cats = ["sentinel", "human", "horse", "chicken", "emu", "deer", "other"]

    dict_list = []
    for i in range(len(test_data)):
        county = test_data.iloc[i]['county']
        activity_merged_string = test_data.iloc[i]['activity']

        activity_sep = activity_merged_string.split(")")
        activity_sep = [x for x in activity_sep if len(x) > 0]

        county_dict = create_dict(disease_cat_list)
        county_dict['county'] = county
        county_dict['week'] = week

        for entry in activity_sep:
            disease_in_entry = False
            test_dis_list = [x+":" for x in disease_cat_list]
            for disease in test_dis_list:
                if disease in entry:
                    found_disease = disease
                    disease_in_entry = True

            if disease_in_entry:
                entry = entry.split(found_disease)[1]

            subcat_in_entry = False
            for sub_cat in disease_sub_cats:
                if sub_cat in entry:
                    found_sub_cat = sub_cat
                    subcat_in_entry = True

            if subcat_in_entry:
                count = entry.split(found_sub_cat)[0]
                symbol_list = [";", ",", ":"]
                for symbol in symbol_list:
                    if symbol in count:
                        count = count.replace(symbol, "")
                count = int(count)
            else:
                count = 0

            county_dict[found_disease.replace(":", "")][found_sub_cat] = count

        dict_list.append(county_dict)

    df = pd.json_normalize(dict_list)
    return df


#Extract case dates from pdf
def extract_case_dates(pdf_filepath):
    PdfReader = PyPDF2.PdfReader(pdf_filepath)
    num_pages = len(PdfReader.pages)
    text = ''
    for page_number in range(num_pages):
        page = PdfReader.pages[page_number]
        page_text = page.extract_text()
        text = text + page_text

    date_pattern = re.compile(r'\b\d{1,2}/\d{1,2}/(?:\d{2}|\d{4})\b')
    dates = date_pattern.findall(text)
    print(f"Extracted dates from {pdf_filepath}: {dates}")  # Debugging line
    return dates

def get_weekly_case_counts(dates):
    if not dates:
        print("No dates found in any of the PDFs.")
        return []

    date_format = "%m/%d/%y"  
    dates = [datetime.strptime(date, date_format) for date in dates]
    start_date = min(dates)
    end_date = max(dates)
    current_date = start_date
    weekly_counts = []

    while current_date <= end_date:
        week_end_date = current_date + timedelta(days=6)
        count = sum(1 for date in dates if current_date <= date <= week_end_date)
        weekly_counts.append((current_date.strftime("%m/%d/%Y"), count))  
        current_date = week_end_date + timedelta(days=1)

    return weekly_counts

base_url = "https://www.floridahealth.gov/diseases-and-conditions/mosquito-borne-diseases/"
url = "https://www.floridahealth.gov/diseases-and-conditions/mosquito-borne-diseases/surveillance.html"

response = requests.get(url)
if response.status_code == 200:
    html_content = response.text

soup = BeautifulSoup(html_content, 'html.parser')
year_2014_div = soup.find('div', class_='reportYear 2014')

if year_2014_div:
    report_links = year_2014_div.find_all('a', class_='list-group-item')
    report_data = [(a.text.strip(), a.get('href')) for a in report_links]
else:
    report_data = []

counties = ['Alachua', 'Baker', 'Bay', 'Bradford', 'Brevard', 'Broward', 'Calhoun', 'Charlotte', 'Citrus', 'Clay', 'Collier', 'Columbia',
            'DeSoto', 'Dixie', 'Duval', 'Escambia', 'Flagler', 'Franklin', 'Gadsden', 'Gilchrist', 'Glades', 'Gulf', 'Hamilton', 'Hardee',
            'Hendry', 'Hernando', 'Highlands', 'Hillsborough', 'Holmes', 'Indian River', 'Jackson', 'Jefferson', 'Lafayette', 'Lake', 'Lee',
            'Leon', 'Levy', 'Liberty', 'Madison', 'Miami-Dade', 'Manatee', 'Marion', 'Martin', 'Monroe', 'Nassau', 'Okaloosa', 'Okeechobee',
            'Orange', 'Osceola', 'Palm Beach', 'Pasco', 'Pinellas', 'Polk', 'Putnam', 'St. Johns', 'St. Lucie', 'Santa Rosa', 'Sarasota',
            'Seminole', 'Sumter', 'Suwannee', 'Taylor', 'Union', 'Volusia', 'Wakulla', 'Walton', 'Washington']

manual_examine_weeks = []



os.makedirs('fl_pdf_files', exist_ok=True)
all_counts_df = []
all_dates = []


for week, link in report_data:
    if week not in manual_examine_weeks:
        pdf_url = base_url + link
        response = requests.get(pdf_url)
        pdf_file = os.path.join('fl_pdf_files', f'{week}.pdf')
        with open(pdf_file, 'wb') as f:
            f.write(response.content)
        data_text = get_table_text(pdf_file, counties)
        arbovirus_activity_data = extract_arbovirus_activity(data_text)
        counts_df = generate_counts_df(arbovirus_activity_data, week, datetime.now().strftime("%Y-%m-%d"))
        all_counts_df.append(counts_df)
        case_dates = extract_case_dates(pdf_file)
        all_dates.extend(case_dates)

print(f"Total dates extracted: {len(all_dates)}")  # Debugging line

if all_dates:
    weekly_case_counts = get_weekly_case_counts(all_dates)
    print("Weekly case counts:", weekly_case_counts)
else:
    print("No dates were extracted from any of the PDFs.")

combined_counts_df = pd.concat(all_counts_df, ignore_index=True)

combined_counts_df['county'] = combined_counts_df['county'].str.replace('IndianRiver', 'Indian River')
combined_counts_df['county'] = combined_counts_df['county'].str.replace('PalmBeach', 'Palm Beach')
combined_counts_df['county'] = combined_counts_df['county'].str.replace('St.Johns', 'St. Johns')
combined_counts_df['county'] = combined_counts_df['county'].str.replace('St.Lucie', 'St. Lucie')
combined_counts_df['county'] = combined_counts_df['county'].str.strip().str.lower()
counties = [county.lower() for county in counties]

filter1 = combined_counts_df[combined_counts_df['county'].isin(counties)]

print(filter1)
filter1.to_csv('fl_arbovirus_counts14.csv', index=False)

#Get weekly case counts
weekly_case_counts = get_weekly_case_counts(all_dates)
