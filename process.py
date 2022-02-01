"""
Copyright, 2021-2022 Ontocord, LLC, All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import re
import fsspec
from collections import Counter
from  datasets import load_dataset
from transformers import AutoTokenizer, RobertaForTokenClassification, M2M100ForConditionalGeneration, M2M100Tokenizer, pipelines
import spacy
from tqdm import tqdm
import difflib
from transformers import pipeline, MarianMTModel, XLMRobertaForTokenClassification, BertForTokenClassification, ElectraForTokenClassification
import random
from sentence_transformers import SentenceTransformer
from torch.nn.functional import cosine_similarity
import langid
import json
import os
import gzip
import re, regex
import itertools
import torch
from sentence_transformers import SentenceTransformer
try:
  if stopwords is None:
    from stopwords import stopwords
except:
  try:
    from stopwords import stopwords
  except:
    stopwords = {}
try:
  if english_flagged_words is None:
    from flagged_words import *
except:
  try:
    from flagged_words import *
  except:
    english_flagged_words = {}
    flagged_words = {}

from faker import Faker
from faker.providers import person, company, geo, address, ssn
import qg_pipeline

from mariam_mt import mariam_mt
try:
  import neuralcoref
except:
  neuralcoref = None
  pass

def try_decode(text):
   try: 
     return text.decode().strip()
   except: 
     return None



faker_list = [
    'ar_AA',
    'ar_PS',
    'ar_SA',
    'bg_BG',
    'cs_CZ',
    'de_AT',
    'de_CH',
    'de_DE',
    'dk_DK',
    'el_GR',
    'en_GB',
    'en_IE',
    'en_IN',
    'en_NZ',
    'en_TH',
    'en_US',
    'es_CA',
    'es_ES',
    'es_MX',
    'et_EE',
    'fa_IR',
    'fi_FI',
    'fr_CA',
    'fr_CH',
    'fr_FR',
    'fr_QC',
    'ga_IE',
    'he_IL',
    'hi_IN',
    'hr_HR',
    'hu_HU',
    'hy_AM',
    'id_ID',
    'it_IT',
    'ja_JP',
    'ka_GE',
    'ko_KR',
    'lt_LT',
    'lv_LV',
    'ne_NP',
    'nl_NL',
    'no_NO',
    'or_IN',
    'pl_PL',
    'pt_BR',
    'pt_PT',
    'ro_RO',
    'ru_RU',
    'sl_SI',
    'sv_SE',
    'ta_IN',
    'th_TH',
    'tr_TR',
    'tw_GH',
    'uk_UA',
    'zh_CN',
    'zh_TW']

faker_map = {}

for faker_lang in faker_list:
  lang, _ = faker_lang.split("_")
  faker_map[lang] = faker_map.get(lang, []) + [faker_lang]

def _get_oscar_urls(language, shuffled="unshuffled", deduplicated="deduplicated"):
  _BASE_DATA_URL_FORMAT_STR = ("https://s3.amazonaws.com/datasets.huggingface.co/oscar/1.0/{shuffled}/{deduplicated}/{language}/")
  _BASE_CHECKSUM_FILE_NAME = "{language}_sha256.txt"
  base_data_url = _BASE_DATA_URL_FORMAT_STR.format(
            shuffled=shuffled, language=language, deduplicated=deduplicated
        )
  checksum_url = base_data_url + _BASE_CHECKSUM_FILE_NAME.format(language=language)
  with fsspec.open(checksum_url, encoding="utf-8") as f:
    data_filenames = [line.decode().split("\t")[0] for line in f if line]
    return [base_data_url + data_filename for data_filename in data_filenames]

def _download_urls(urls):
  for url in urls:
    if not os.path.exists(url.split("/")[-1]):
      os.system(f"wget {url}")



trannum = str.maketrans("0123456789", "1111111111")

#use english firstnames for now
bantu_surnames = ["Dlamini", "Gumede", "Hadebe", "Ilunga", "Kamau", "Khoza", "Lubega", "M'Bala", "Mabaso", "Mabika",
                  "Mabizela", "Mabunda", "Mabuza", "Macharia", "Madima", "Madondo", "Mahlangu", "Maidza", "Makhanya",
                  "Malewezi", "Mamba", "Mandanda", "Mandlate", "Mangwana", "Manjate", "Maponyane", "Mapunda", "Maraire",
                  "Masango", "Maseko", "Masemola", "Masengo", "Mashabane", "Masire", "Masondo", "Masuku", "Mataka",
                  "Matovu", "Mbala", "Mbatha", "Mbugua", "Mchunu", "Mkhize", "Mofokeng", "Mokonyane", "Mutombo",
                  "Ncube", "Ndagire", "Ndhlovu", "Ndikumana", "Ndiritu", "Ndlovu", "Ndzinisa", "Ngcobo", "Nkomo",
                  "Nkosi", "Nkurunziza", "Radebe", "Tshabalala", "Tshivhumbe", "Vila"]
#male and female
vietnamese_firstnames = ["Anh", "Dung", "Hanh", "Hoa", "Hong", "Khanh", "Lan", "Liem", "Nhung", "Duy", "Xuan"]
vietnamese_surnames = ["Nguyễn","Trần","Lê","Phạm","Hoàng","Huỳnh","Phan","Vũ","Võ", "Đặng","Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý"]

#use english firstnames for now
bengali_surnames  = ["Banerjee", "Bagchi", "Bhaduri", "Bhattacharjee", "Chakraborty", "Chatterjee", "Ganguly", "Goswami", "Ghoshal", "Lahiri", "Maitra", "Mukherjee", "Sanyal", "Chakraborty", "Bhattacharya", "Baidya", "Sengupta", "Dasgupta", "Duttagupta", "Gupta", "Sen-Sharma", "Basu", "Bose", "Dutta", "Ghosh", "Choudhury", "Guha", "Gain", "Mitra", "Singh", "Sinha", "Sen", "Pal", "De", "Dey", "Deb", "Dev", "Jana", "Palit", "Chanda", "Chandra", "Das", "Dam", "Kar", "Nandi", "Sarkar", "Nag", "Som"]

#male and female
urdu_firstnames = ["Azhar", "Benazir", "Farahnaz", "Maliha", "Minoo", "Romana", "Sania", "Azhar", "Burhan", "Changezi", "Faizan", "Fasih", "Fuad", "Hassim", "Jan", "Shoaib"]
urdu_surnames = ["Abid", "Ahmad", "Akbar", "Akmal", "Alam", "Ayaz", "Bohra", "Bucha", "Bukhari", "Buksh", "Bux", "Chandpuri", "Changezi", "Emani", "Farrukhabadi", "Farrukhi", "Fazail", "Hassim", "Hilaly", "Hussaini ", "Brahmin", "Lucknawi", "Ludhianvi", "Matloob", "Omar", "Vaishya", "Rahimtoola", "Shafiq", "Shoaib", "Siddiqui", "Siddiqui", "Tikka", "Yasser", ]

#basque and catalan - use Spanish names

class TextAugment:

  m2m_model = None
  m2m_tokenizer = None 
  en_spacy_nlp = None 
  en_stopwords = set(stopwords['en'])
  faker_en_list  = None
  labse = None
  
  #from https://github.com/madisonmay/CommonRegex/blob/master/commonregex.py which is under the MIT License
  # see also for ICD https://stackoverflow.com/questions/5590862/icd9-regex-pattern - but this could be totally wrong!
  # we do regex in this order in order to not capture ner inside domain names and email addresses.
  regex_rulebase = {
    "NORP": {
      "en": [(re.compile(r"upper class|middle class|working class|lower class", re.IGNORECASE), None),],
    },
    "AGE": {
      "en": [
          (
              re.compile(
                  r"\S+ years old|\S+\-years\-old|\S+ year old|\S+\-year\-old|born [ ][\d][\d]+[\\ /.][\d][\d][\\ /.][\d][\d]+|died [ ][\d][\d]+[\\ /.][\d][\d][\\ /.][\d][\d]+", re.IGNORECASE
              ),
              None,
          )
      ],
      "zh": [(regex.compile(r"\d{1,3}歲|岁"), None)],
    },
    # Some of this code from https://github.com/bigscience-workshop/data_tooling/blob/master/ac_dc/anonymization.py which is under the Apache 2 license
    "ADDRESS": {
      "en": [
              #https://github.com/madisonmay/CommonRegex/blob/master/commonregex.py
              (
                  re.compile(
                      r"\d{1,4} [\w\s]{1,20} (?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|park|parkway|pkwy|circle|cir|boulevard|blvd)\W?(?=\s|$).*\b\d{5}(?:[-\s]\d{4})?\b|\d{1,4} [\w\s]{1,20} (?:street|st|avenue|ave|road|rd|highway|hwy|square|sq|trail|trl|drive|dr|court|ct|park|parkway|pkwy|circle|cir|boulevard|blvd)\W?(?=\s|$)", re.IGNORECASE
                  ),
                  None,
              ),
              (
                  re.compile(r"P\.? ?O\.? Box \d+"), None
              )
      ],
    
      "zh": [
          (
              regex.compile(
                  r"((\p{Han}{1,3}(自治区|省))?\p{Han}{1,4}((?<!集)市|县|州)\p{Han}{1,10}[路|街|道|巷](\d{1,3}[弄|街|巷])?\d{1,4}号)"
              ),
              None,
          ),
          (
              regex.compile(
                  r"(?<zipcode>(^\d{5}|^\d{3})?)(?<city>\D+[縣市])(?<district>\D+?(市區|鎮區|鎮市|[鄉鎮市區]))(?<others>.+)"
              ),
              None,
          ),
      ],
    },
    "DISEASE": {
      "en": [(re.compile("diabetes|cancer|HIV|AIDS|Alzheimer's|Alzheimer|heart disease", re.IGNORECASE), None)],
    }, 
    # many of the id_regex are from Presidio which is licensed under the MIT License
    # https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/aba_routing_recognizer.py 
    # https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/au_abn_recognizer.py
    # https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/us_passport_recognizer.py
    # https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/medical_license_recognizer.py
    # https://github.com/microsoft/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/es_nif_recognizer.py 
    "ID": {
      "en": [
              (
                re.compile(r"\b[0123678]\d{3}-\d{4}-\d\b"),
                (
                    "aba",
                    "routing",
                    "abarouting",
                    "association",
                    "bankrouting",
                ),
              ),
              (
                  re.compile(r"(\b[0-9]{9}\b)"),
                  (
                      "us",
                      "united",
                      "states",
                      "passport",
                      "passport#",
                      "travel",
                      "document",
                  ),
              ),
              (
                  re.compile(r"[a-zA-Z]{2}\d{7}|[a-zA-Z]{1}9\d{7}"),
                  ("medical", "certificate", "DEA"),
              ),
              (re.compile(r"\d{3}\s\d{3}\s\d{3}"), None),
              (
                  re.compile(
                      r"GB\s?\d{6}\s?\w|GB\d{3}\s\d{3}\s\d{2}\s\d{3}|GBGD\d{3}|GBHA\d{3}}|GB\d{3} \d{4} \d{2}(?: \d{3})?|GB(?:GD|HA)\d{3}"
                  ),
                  None,
              ),
              (re.compile(r"IE\d[1-9]\d{5}\d[1-9]|IE\d{7}[1-9][1-9]?"), None),
              (re.compile(r"[1-9]\d{10}"), None),
              (
                  re.compile(
                      r"\d{2}-\d{7}-\d|\d{11}|\d{2}-\d{9}-\d|\d{4}-\d{4}-\d{4}|\d{4}-\d{7}-\d"
                  ),
                  None,
              ),
              (
                  re.compile(r"\b\d{2}\s\d{3}\s\d{3}\s\d{3}\b|\b\d{11}\b"),
                  ("australian business number", "abn"),
              ),
      ],
      "id":[
              (
                  re.compile(
                      r"\d{6}([04][1-9]|[1256][0-9]|[37][01])(0[1-9]|1[0-2])\d{6}"
                  ),
                  None,
              )
      ],
      "es": [
              (re.compile(r"(?:ES)?\d{6-8}-?[A-Z]"), None),
              (
                  re.compile(r"\b[0-9]?[0-9]{7}[-]?[A-Z]\b"),
                  ("documento nacional de identidad", "DNI", "NIF", "identificación"),
              ),
              (re.compile(r"[1-9]\d?\d{6}|8\d{8}|9\d{8}|10\d{8}|11\d{8}|12\d{8}|"), None)
      ],
      "pt": [(re.compile(r"\d{3}\.d{3}\.d{3}-\d{2}|\d{11}"), None),
             (re.compile(r"PT\d{9}"), None),
      ],
      "zh": [
          (
              regex.compile(
                  r"(?:[16][1-5]|2[1-3]|3[1-7]|4[1-6]|5[0-4])\d{4}(?:19|20)\d{2}(?:(?:0[469]|11)(?:0[1-9]|[12][0-9]|30)|(?:0[13578]|1[02])(?:0[1-9]|[12][0-9]|3[01])|02(?:0[1-9]|[12][0-9]))\d{3}[\dXx]"
              ),
              None,
          ),
          (
              regex.compile(
                  r"(^[EeKkGgDdSsPpHh]\d{8}$)|(^(([Ee][a-fA-F])|([DdSsPp][Ee])|([Kk][Jj])|([Mm][Aa])|(1[45]))\d{7}$)"
              ),
              None,
          ),
          (
              regex.compile(
                  r"((\d{4}(| )\d{4}(| )\d{4}$)|([a-zA-Z][1-2]{1}[0-9]{8})|([0-3]{1}\d{8}))"
              ),
              None,
          ),
          (
              regex.compile('^(?:[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领 A-Z]{1}[A-HJ-NP-Z]{1}(?:(?:[0-9]{5}[DF])|(?:[DF](?:[A-HJ-NP-Z0-9])[0-9]{4})))|(?:[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领 A-Z]{1}[A-Z]{1}[A-HJ-NP-Z0-9]{4}[A-HJ-NP-Z0-9 挂学警港澳]{1})$'), 
              None
          ),
          (
              regex.compile('\b[A-Z]{3}-\d{4}\b'), 
              None,
          ),
          (
              regex.compile(
                  r"(0?\d{2,4}-[1-9]\d{6,7})|({\+86|086}-| ?1[3-9]\d{9} , ([\+0]?86)?[\-\s]?1[3-9]\d{9})"
              ),
              None,
          ),
          (
              regex.compile(
                  r"((\d{4}(| )\d{4}(| )\d{4}$)|([a-zA-Z][1-2]{1}[0-9]{8})|([0-3]{1}\d{8}))((02|03|037|04|049|05|06|07|08|089|082|0826|0836|886 2|886 3|886 37|886 4|886 49|886 5|886 6|886 7|886 8|886 89|886 82|886 826|886 836|886 9|886-2|886-3|886-37|886-4|886-49|886-5|886-6|886-7|886-8|886-89|886-82|886-826|886-836)(| |-)\d{4}(| |-)\d{4}$)|((09|886 9|886-9)(| |-)\d{2}(|-)\d{2}(|-)\d{1}(|-)\d{3})"
              ),
              None,
          ),
      ],
      "default": [
              #https://github.com/madisonmay/CommonRegex/blob/master/commonregex.py ssn
              (
                  re.compile(
                     '(?!000|666|333)0*(?:[0-6][0-9][0-9]|[0-7][0-6][0-9]|[0-7][0-7][0-2])[- ](?!00)[0-9]{2}[- ](?!0000)[0-9]{4}'
                  ),
                  None,
              ),
              # https://github.com/madisonmay/CommonRegex/blob/master/commonregex.py phone with exts
              (
                  re.compile('((?:(?:\+?1\s*(?:[.-]\s*)?)?(?:\(\s*(?:[2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9])\s*\)|(?:[2-9]1[02-9]|[2-9][02-8]1|[2-9][02-8][02-9]))\s*(?:[.-]\s*)?)?(?:[2-9]1[02-9]|[2-9][02-9]1|[2-9][02-9]{2})\s*(?:[.-]\s*)?(?:[0-9]{4})(?:\s*(?:#|x\.?|ext\.?|extension)\s*(?:\d+)?))', re.IGNORECASE),
                  None
              ),
              # phone
              (
                  re.compile('''((?:(?<![\d-])(?:\+?\d{1,3}[-.\s*]?)?(?:\(?\d{3}\)?[-.\s*]?)?\d{3}[-.\s*]?\d{4}(?![\d-]))|(?:(?<![\d-])(?:(?:\(\+?\d{2}\))|(?:\+?\d{2}))\s*\d{2}\s*\d{3}\s*\d{4}(?![\d-])))'''),
                  None,
              ),
              #email
              (re.compile("([a-z0-9!#$%&'*+\/=?^_`{|.}~-]+@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)", re.IGNORECASE), None),
              #credit card
              (re.compile('((?:(?:\\d{4}[- ]?){3}\\d{4}|\\d{15,16}))(?![\\d])'), None), 
              #ip
              (re.compile('(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)', re.IGNORECASE), None), 
              #ipv6
              (re.compile('((?:(?:\\d{4}[- ]?){3}\\d{4}|\\d{15,16}))(?![\\d])'), None),
              #icd code - see https://stackoverflow.com/questions/5590862/icd9-regex-pattern
              (re.compile('[A-TV-Z][0-9][A-Z0-9](\.[A-Z0-9]{1,4})'), None), 
              # generic government id. consider a more complicated string with \w+ at the beginning or end
              (re.compile(r"\d{8}|\d{9}|\d{10}|\d{11}"), None), 
      ],
    },   
  }


  # see https://www.researchgate.net/publication/259179064_Comparing_Methods_for_Detecting_Child_Exploitation_Content_Online for common CSAM words
  # http://antipaedo.lip6.fr/T12/keywords_cnrs.pdf - for top 20 from table 7 and 8 of the paper, plus other similar words , ignoring stopwords like "tuesday"
  # WARNING: Translations are probably not accurate. TODO to fix.
  # we are only doing our current covered langauges. TODO, do for all languages.
  banned_words = {
      'ar': {"فتاة صغيرة" , "فتاة صغيرة" , "فتى صغير", "مراهق" , "لولي" , "لولا" , "لوليتا" , "لولي" , "لولي" , "لوليتاغوي" , "فتاة" , "صبي" ,"طفل" , "حمام" },
      'ur': {'نوجوان لڑکی', 'چھوٹی لڑکی', 'چھوٹا لڑکا', 'نوجوان لڑکا','نوعمر','لولی','لولا','لولیتا','لولی','لولی','لولیتاگو','لڑکی','لڑکا','بچہ','بچہ','غسل', 'غسل', 'غسل'},
      'bn': {'ছোট মেয়ে', 'ছোট মেয়ে', 'ছোট ছেলে', 'কিশোর', 'ললি', 'লোলা', 'ললিতা', 'ললি', 'লোলি', 'ললিটাগুই', 'মেয়ে', 'ছেলে' , 'শিশু', 'স্নান',},
      'hi': {'युवा लड़की', 'छोटी लड़की', 'छोटा लड़का', 'किशोर', 'लॉली', 'लोला', 'लोलिता', 'लल्ली', 'लोली', 'लोलितागुय', 'लड़की', 'लड़का' , 'बच्चा', 'स्नान',},
      'eu': {'neska gaztea', 'neska txikia', 'mutil txikia', 'nerabea', 'neska', 'mutil' , 'haurra', 'bainua',},
      'ca': {'noia', 'nena', 'nen petit', 'nen' , 'nen', 'banyer',},
      'vi': {'thiếu niên', 'cậu nhỏ', 'cậu bé', 'cô gái trẻ', 'cô bé', 'cậu bé', 'trẻ em', 'tắm', },
      'zh': {'儿童','女孩','孩子', '小女孩', '小姑娘','小男孩', '年輕女孩','年轻女孩','年轻的女孩','洗澡','洛丽塔','洛麗塔','浴','男孩','萝拉','萝莉','萝莉塔吉','蘿拉','蘿莉','蘿莉塔','青少年'},
      'fr': {'jeune fille','petite fille','petit garçon','ado',  'fille', 'garçon' , 'enfant', 'bain',},
      'id': {'gadis muda','gadis kecil','anak laki-laki kecil','remaja',  'perempuan', 'laki-laki' , 'anak', 'mandi',},
      'fa': {'دختر جوان',  'دختر کوچولو',  'پسر کوچولو',  'نوجوان',  'لولی',  'لولا',  'لولیتا',  'لولی',  'لولی',  'لولیتاگو',  'دختر',  'پسر' ,'کودک',  'حمام', },
      'ur': {'نوجوان لڑکی',  'چھوٹی لڑکی',  'چھوٹا لڑکا',  'نوعمر',  'لولی',  'لولا',  'لولیتا',  'لولی',  'لولی',  'لولیتاگوئے',  'لڑکی',  'لڑکا' ,'بچہ',  'غسل', },
      'es': {'niña',  'niño', 'adolescente', 'baño',},
      'pt': {'menina', 'menino', 'adolescente', 'pirulito',  'criança', 'banho',},
      'ig': {'nwa agbọghọ', 'nwa agbọghọ', 'nwa agbọghọ',' iri na ụma', 'nwa agbọghọ', 'nwoke' , 'nwa', },
      'sw': {'msichana mdogo','msichana mdogo','kijana mdogo', 'mtoto', 'kuoga',},
      'yo': {'kekere', 'omobinrin', 'omokunrin', 'ọmọ', 'wẹwẹ',},
      'xh': {'intombazana encinci', 'intsha', 'umntwana', 'hlamba', 'inkwenkwe', },
      'zu': {'intombazane', 'intsha', 'intombazane encane',  'umfana omncane','geza', 'ingane', 'yomfana'},
      'default': {'young girl', 'little girl','little boy', 'young boy', 'teen', 'lolli', 'lola', 'lolita', 'lolly', 'loli', 'lolitaguy', 'girl', 'boy', 'child', 'kid',  \
                  'bath', 'baths', 'bathing', "pedo", 'nymphet', 'nimphet', 'babyj', 'voglia', 'eurololita', '349', 'hussyfan', 'kidzilla', 'raygold', 'ygold', 'qwerty', 'qqaazz', 'ptsc', \
                  'pthc', 'nn', 'tanta', 'mylola', 'arina', 'newstar', 'playtoy', 'imouto', 'lourinha', 'amateurz', 'kacy', 'vicky', 'lsm', 'sandra', \
                  'babyshivid', 'shiori', 'tvg', 'chiharu','kidzilla', 'izzy', 'rika', 'kdquality', 'cbaby', 'nablot', 'lso',  'kinderficker', \
                  'yo',  'yr',  }
  }
  # note that we do not have a transformer model for catalan, but  we use transfer learning from Davlan/xlm-roberta-base-ner-hrl. We could also use spacy's catalan model
  hf_ner_model_map = {
      "sn": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0]], # consider using one of the smaller models
      "st": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0]], # consider using one of the smaller models
      "ny": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0]], # consider using one of the smaller models
      "xh": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0]], # consider using one of the smaller models
      "zu": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0]], # consider using one of the smaller models
      "sw": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0]], # consider using one of the smaller models
      "yo": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0 ]], 
      "ig": [["Davlan/xlm-roberta-large-masakhaner", XLMRobertaForTokenClassification, 1.0 ]], 
      "ar": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 1.0]],
      "en": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 1.0], ["bioformers/bioformer-cased-v1.0-ncbi-disease", BertForTokenClassification, 1.0]], #["jplu/tf-xlm-r-ner-40-lang", None ],
      "es": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 1.0 ]],
      "eu": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 0.8 ]],
      "ca": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 0.8 ]],
      "pt": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 1.0 ]], 
      "fr": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 1.0 ]],
      #"zh": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 1.0], ["zh_model", XLMRobertaForTokenClassification, 0.9 ]],
      "zh": [["Davlan/xlm-roberta-base-ner-hrl", XLMRobertaForTokenClassification, 1.0 ]],
      'vi': [["lhkhiem28/COVID-19-Named-Entity-Recognition-for-Vietnamese", RobertaForTokenClassification, 1.0]],#["jplu/tf-xlm-r-ner-40-lang", None ], 
      'hi': [["jplu/tf-xlm-r-ner-40-lang", None, 1.0 ]],
      'ur': [["jplu/tf-xlm-r-ner-40-lang", None, 1.0 ]],
      'id': [["cahya/bert-base-indonesian-NER", BertForTokenClassification, 1.0]], 
      'bn': [["sagorsarker/mbert-bengali-ner", BertForTokenClassification, 1.0]],

      # NOT PART OF OUR LANGUAGE SET. EXPERIMENTAL
      'he': [["jplu/tf-xlm-r-ner-40-lang", None, 1.0 ]],
      'hr': [["classla/bcms-bertic-ner", ElectraForTokenClassification, 1.0]],
      'bs': [["classla/bcms-bertic-ner", ElectraForTokenClassification, 1.0]],
      'sr': [["classla/bcms-bertic-ner", ElectraForTokenClassification, 1.0]],
      'cnr': [["classla/bcms-bertic-ner", ElectraForTokenClassification, 1.0]],
      'hbs': [["classla/bcms-bertic-ner", ElectraForTokenClassification, 1.0]],
      'da': [["saattrupdan/nbailab-base-ner-scandi", BertForTokenClassification, 1.0]],
      'no': [["saattrupdan/nbailab-base-ner-scandi", BertForTokenClassification, 1.0]],
      'nb': [["saattrupdan/nbailab-base-ner-scandi", BertForTokenClassification, 1.0]],
      'nn': [["saattrupdan/nbailab-base-ner-scandi", BertForTokenClassification, 1.0]],
      'sv': [["saattrupdan/nbailab-base-ner-scandi", BertForTokenClassification, 1.0]],
      'fo': [["saattrupdan/nbailab-base-ner-scandi", BertForTokenClassification, 1.0]],
      'is': [["saattrupdan/nbailab-base-ner-scandi", BertForTokenClassification, 1.0]],
      }
  translation_pipelines = {}
  ner_model_name2pipelines = {}  
  strip_chars = " ,،、{}[]|()\"'“”《》«»?!:;?…"
  punc_char = ".?!:;?。…"
  special_char = " ,{}[]()|\\\"'“”《》«»~!@#$%^&*{}[]()_+=-0987654321`<>,、،./?':;“”\"\t\n\\πه☆●¦″．۩۱（☛₨➩°・■↑☻、๑º‹€σ٪’Ø·−♥ıॽ،٥《‘©。¨﴿！★×✱´٬→±x：¹？£―▷ф¡Г♫∟™ª₪®▬「—¯；¼❖․ø•�」٣，٢◦‑←§١ー٤）˚›٩▼٠«¢¸٨³½˜٭ˈ¿¬ι۞⌐¥►†ƒ∙²»¤…﴾⠀》′ا✓→¶'"
  junk = set(",{}[]()|\\\"'“”《》«»~!@#$%^&*{}[]()_+=-0987654321`<>,、،./?':;“”\"\t\n\\πه☆●¦″．۩۱（☛₨➩°・■↑☻、๑º‹€σ٪’Ø·−♥ıॽ،٥《‘©。¨﴿！★×✱´٬→±x：¹？£―▷ф¡Г♫∟™ª₪®▬「—¯；¼❖․ø•�」٣，٢◦‑←§١ー٤）˚›٩▼٠«¢¸٨³½˜٭ˈ¿¬ι۞⌐¥►†ƒ∙²»¤…﴾⠀》′ا✓→¶'")
  #don't add a space for junk chars
  ontology_manager = None
  max_stoword_len_zh = max([0]+[len(a) for a in stopwords.get('zh', [])])
  max_stoword_len_ko = max([0]+[len(a) for a in stopwords.get('ko', [])])
  max_stoword_len_ja = max([0]+[len(a) for a in stopwords.get('ja', [])])
  stopwords_en = set(stopwords.get('en',[]))


  def __init__(self):

    try:
      TextAugment.labse = labse 
      TextAugment.ontology_manager = ontology_manager
      TextAugment.translation_pipelines = translation_pipelines
      TextAugment.ner_model_name2pipelines = ner_model_name2pipelines
      TextAugment.en_spacy_nlp = en_spacy_nlp
      TextAugment.faker_en_list = faker_en_list
      TextAugment.qg = qg
    except: # use the below for production usage. the above is for testing. 
      if TextAugment.en_spacy_nlp is None: TextAugment.en_spacy_nlp = spacy.load('en_core_web_sm')
      try:
        coref = neuralcoref.NeuralCoref(TextAugment.en_spacy_nlp.vocab)
        TextAugment.en_spacy_nlp.add_pipe(coref, name='neuralcoref')
        #we could potentially add new items to the vocabulary to improve coref.
      except:
        pass
      if TextAugment.qg is None: TextAugment.qg = qg_pipeline.pipeline("multitask-qa-qg") # TODO make sure it's running in half mode
      if TextAugment.labse is None: TextAugment.labse =  SentenceTransformer("sentence-transformers/LaBSE").half().eval().cuda()
      if TextAugment.ontology_manager is None: TextAugment.ontology_manager = None # OntologyManager(src_lang='en') #src_lang=src_lang
      if TextAugment.faker_en_list is None:
        TextAugment.faker_en_list  = faker_en_list = [Faker(faker_lang) for faker_lang in faker_map["en"]]
        for faker_en in faker_en_list:
          faker_en.add_provider(person)
          faker_en.add_provider(ssn)
          faker_en.add_provider(address)
          faker_en.add_provider(company)
    print ("finished load")

  def check_good_sentence(self, s, src_lang, stopwords, stopword_ratio_cutoff=0.06, bannedwords=None, flagged_words=None, badword_ratio_cutoff=0.15,  junk_ratio=0.16, max_badword_len=5):
    #basic dejunk
    # for flagged_words, only filter out if the ratio is exceeded AND there exists one banned word
    if bannedwords is None:
      bannedwords = self.banned_words.get(src_lang, self.banned_words['default'])
    default_bannedwords = self.banned_words['default']
    s = s.lower().strip()
    if not s: return False
    #print ([s2 for s2 in s if s2 in self.junk])
    #print (len([s2 for s2 in s if s2 in self.junk]), len(s))
    jr = len([s2 for s2 in s if s2 in self.junk])/len(s)
    if jr >= junk_ratio:
      return False
    if src_lang in ("ja", "ko", "zh"):
      sArr = s
    else:
      sArr = [s2.strip(self.special_char) for s2 in s.lower().split() if s2.strip(self.special_char)]
    if len(sArr) == 0:
      return False
    #stopword check
    if stopwords is not None:
      #TODO: catch multi word with spaces
      #print ('sw', len([s2 for s2 in sArr if s2 in stopwords])/len(sArr))
      if src_lang not in ("ja", "ko", "zh") and len([s2 for s2 in sArr if s2 in stopwords])/len(sArr) < stopword_ratio_cutoff:
        return False
      if src_lang in ("ja", "ko", "zh"):
        if src_lang == "zh":
          max_stoword = self.max_stoword_len_zh
        elif src_lang == "ko":
          max_stoword = self.max_stoword_len_ko
        elif src_lang == "ja":
          max_stoword = self.max_stoword_len_ja
        len_s = len(s)
        stop_cnt = 0
        total_cnt = 0
        for i in range(len_s):
          for j in range(i+1,min(len_s, i+max_stoword)):
            if s[i:j] in stopwords:
              stop_cnt += 1
            total_cnt += 1
        #print ('stopword', (stop_cnt/total_cnt) )
        if (stop_cnt/total_cnt) < stopword_ratio_cutoff:
          return False
    if flagged_words is not None:
      #print ('bw', len([s2 for s2 in sArr if s2 in flagged_words])/len(sArr))
      if src_lang not in ("ja", "ko", "zh") and len([s2 for s2 in sArr if s2 in flagged_words])/len(sArr) > badword_ratio_cutoff:
        if any(s2 for s2 in sArr if s2 in bannedwords) or any(s2 for s2 in sArr if s2 in default_bannedwords):
          return False
      if src_lang in ("ja", "ko", "zh"):
        badword_ratio_cutoff /= 100
        len_s = len(s)
        bad_cnt = 0
        total_cnt = 0
        for i in range(len_s):
          for j in range(i+1,min(len_s, i+max_badword_len)):
            if s[i:j] in flagged_words:
              bad_cnt += 1
            total_cnt += 1
        if (bad_cnt/total_cnt) > badword_ratio_cutoff:
          for bword in bannedwords:
            if bword in s: 
              return False
          for bword in default_bannedwords:
            if bword in s: 
              return False
    #langid check
    try:
        lang =  langid.classify(s)[0]
    except:
        return True
    return lang == src_lang

  #WIP - we use this method to extract people, place and thing, and potentially age/date
  def generate_questions(self, batch, default_answers=[]):
    answers = {}

    i= 0
    allqa = []
    for chunk in batch:
      text = chunk['text']
      answers1={}
      #ti = time.time()
      text = text.replace("U.S.","US").replace("\n", " ").replace(",", " , ").replace("  ", " ").strip().replace(" , ", ", ") # replace(" He ", " Lincoln ").replace(" he ", " Lincoln ").replace(" him ", " Lincoln ")
      aHash = self.qg(text) # , default_answers=default_answers)
      allqa.append(aHash)
      default_answers = list(set([a['answer'] for a in aHash]+default_answers))
      print (aHash)
      #for aHash1 in aHash:
      #  extraction = vis.parse(list(dep_parser(aHash1['question']).sents)[0], aHash1['answer'])
      #  print (extraction.arg1, '*', extraction.rel, '*', extraction.arg2)

      for aHash1 in aHash:
        if answers.get(aHash1['answer'].lower()) or answers1.get(aHash1['answer'].lower()):
          continue
        if len(aHash1['answer'].split()) > 10:
          aHash1['answer'] = " ".join(aHash1['answer'].split()[:10])
        i+=1
        quest=aHash1['question'].lower().strip("?").replace("'s",  " 's").replace("  ", " ").split()
        label=""
        #TODO, use spacy_en to get NER and only fall back to "who", "when", "where" to determine ner if we find nothing
        if quest[0] == "who" and aHash1['answer'][-1] =='s':
          label="organization_"+str(i)
          if "'s" in quest:
            for j in range(len(quest)):
              if j > 0 and quest[j-1]=="'s":
                label = quest[j]+"_"+str(i)
                break
          for a in aHash1['answer'].lower().split():
            if a not in stopwords_hash:
              answers[a] = label
        elif quest[0] == "who":
          label="person_"+str(i)
          if "'s" in quest:
            for j in range(len(quest)):
              if j > 0 and quest[j-1]=="'s":
                label = quest[j]+"_"+str(i)
                break
          for a in aHash1['answer'].lower().split():
            if a not in stopwords_hash:
              answers[a] = label
        elif quest[0] == "where":
          label="location_"+str(i)
        elif quest[0] == "when":
          label="date_or_time_"+str(i)
        elif quest[0] == "why":
          label="reason_"+str(i)
        elif quest[0] == "how" and quest[1] in ("much", "many"):
          label="quantity_"+str(i)
        elif quest[0] == "how":
          label="method_"+str(i)
        elif quest[0] in ("which", "what") and quest[1] not in stopwords_hash:
          label=quest[1]+"_"+str(i)
        elif "'s" in quest:
          for j in range(len(quest)):
            if j > 0 and quest[j-1]=="'s":
              label = quest[j]+"_"+str(i)
              break
        if label:
          answers[aHash1['answer'].lower()] = label


        #for b in a['answer'].lower().split():
        #  answers[b] = label
      print (answers)

    for aHash in allqa:
      answers1={}
      for aHash1 in aHash:
        if answers1.get(aHash1['answer'].lower()):
          continue
        quest = " "+aHash1['question'].lower().strip("?").replace("'s",  " 's").replace("  ", " ")+" "
        q_type =  quest[0]
        agent = []
        answer_keys = list(answers.keys())
        answer_keys.sort(key=lambda k: len(k), reverse=True)
        for a in answer_keys:
          if " "+a+" " in quest:
              quest = quest.replace(" "+a+" ", " "+answers[a]+" ")
          elif " "+a+", " in quest:
              quest = quest.replace(" "+a+", ", " "+answers[a]+", ")
        quest = quest.split()
        #print (quest)
        qtype = []
        if answers.get(aHash1['answer'].lower()):
          if answers.get(aHash1['answer'].lower()).split("_")[0] == "person":
            qtype = ["is", "who"]
        if not qtype and quest[0] in ("when", "where", "why", "how"): #, "which"
          qtype=[quest[0]]
          if quest[0]=="how" and quest[1] in ("much", "many"):
            qtype = qtype + [quest[1]]

        #label=[q for q in quest if (q not in ("much", "many",) and not stopwords_hash.get(q) and q not in answers)]#+qtype
        label=[q for q in quest if (q[0] not in "0123456789") and (q not in ("the", "a", "an"))]
        if len(label) > 10:
            label=label[:10]
        answers1[aHash1['answer'].lower()] = " ".join(label)
      print (answers1)

  @staticmethod
  def get_aligned_text(sent1, sent2, src_lang):
    """
    Given two sentences, find blocks of text that match and that don't match.
    return the blocks, and a matching score.
    Used to extract NER from original language sentence.
    """
    if src_lang in ("ja", "ko", "zh"):
      # splitting on spaces doesn't always work because some languages aren't space separated
      sep = ""
    else:
      sep = " "
      sent1 = sent1.split()
      sent2 = sent2.split()
    aMatch = difflib.SequenceMatcher(None,sent1, sent2)
    score = aMatch.ratio()
    blocks = aMatch.get_matching_blocks()
    blocks2 = []
    prevEndA = 0
    prevEndB = 0
    matchLen = 0
    nonMatchLen = 0
    #print (blocks)
    for blockI in range(len(blocks)):
      if blockI > 0 or (blockI==0 and (blocks[blockI][0] != 0 or blocks[blockI][1] != 0)):
        blocks2.append([sep.join(sent1[prevEndA:blocks[blockI][0]]), sep.join(sent2[prevEndB:blocks[blockI][1]]), 0])
        nonMatchLen += max(blocks[blockI][0] - prevEndA, blocks[blockI][1] - prevEndB)
      if blocks[blockI][2] != 0:
        blocks2.append([sep.join(sent1[blocks[blockI][0]:blocks[blockI][0]+blocks[blockI][2]]), sep.join(sent2[blocks[blockI][1]:blocks[blockI][1]+blocks[blockI][2]]), 1])
        prevEndA = blocks[blockI][0]+blocks[blockI][2]
        prevEndB = blocks[blockI][1]+blocks[blockI][2]
        matchLen += blocks[blockI][2]
    #score = float(matchLen+1)/float(nonMatchLen+1)
    return (blocks2, score)

  def do_translations(self, texts, src_lang='en', target_lang='hi', batch_size=16, do_mariam_mt=False):
    if not do_mariam_mt:
      if self.m2m_tokenizer is None: 
        self.m2m_tokenizer = M2M100Tokenizer.from_pretrained("facebook/m2m100_418M")
      try:
        self.m2m_tokenizer.src_lang = src_lang
        target_lang_bos_token = self.m2m_tokenizer.get_lang_id(target_lang)
        translations = []
        for src_text_list in tqdm(self.batch(texts, batch_size)):
          try:
            batch = self.m2m_tokenizer(src_text_list, return_tensors="pt", padding=True, truncation=True).to('cuda')
          except:
            break
          if self.m2m_model is None:
            self.m2m_model = M2M100ForConditionalGeneration.from_pretrained("facebook/m2m100_418M").eval().half().cuda()
          gen = self.m2m_model.generate(**batch, forced_bos_token_id=target_lang_bos_token, no_repeat_ngram_size=4, ) #
          outputs = self.m2m_tokenizer.batch_decode(gen, skip_special_tokens=True)
          translations.extend(outputs)
        return translations
      except:
       pass
    translations = []
    #mariam_mt = self.mariam_mt
    model_name = mariam_mt.get((src_lang, target_lang))
    mt_pipeline = None
    if model_name is not None and model_name not in self.translation_pipelines:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name).half().eval().cuda()
        mt_pipeline = pipeline("translation", model=model, tokenizer=tokenizer, device=0)
        self.translation_pipelines[model_name] = mt_pipeline
        if not mt_pipeline:
          raise RuntimeError("no translation pipeline") # we could do multi-step translation where there are no pairs
    mt_pipeline = self.translation_pipelines[model_name]
    for src_text_list in tqdm(self.batch(texts, batch_size)):
        outputs = [t['translation_text'] for t in mt_pipeline(src_text_list)]
        translations.extend(outputs)
    return translations
  
  @staticmethod
  def cjk_detect(texts):
    # korean
    if re.search("[\uac00-\ud7a3]", texts):
        return "ko"
    # japanese
    if re.search("[\u3040-\u30ff]", texts):
        return "ja"
    # chinese
    if re.search("[\u4e00-\u9FFF]", texts):
        return "zh"
    return None

  @staticmethod
  def batch(lst, n):
    """Generate batches"""
    lst = list(lst)
    for i in range(0, len(lst), n):
        yield lst[i: i + n]



  def apply_regex_ner(self, src_lang, docs, context_window = 20, weight = 1.0, text_key=None, ner_key=None):
    """
    apply regexes from the rulebase. if there is a context, check if the context is met in the context_window. 
    """
    if ner_key is None:
      ner_key = f'{src_lang}_ner'
    if text_key is None:
      text_key = f'{src_lang}_text'
    for doc in docs.values():
      ner = doc[ner_key] = doc.get(ner_key, {})
      sentence = doc[text_key]
      if ner is None: ner = {}
      if src_lang in ("zh", "ko", "ja"):
          sentence_set = set(sentence.lower())
      else:
          sentence_set = set(sentence.lower().split(" "))
      idx = 0
      all_ner = []
      original_sentence = sentence
      for tag, regex_group in self.regex_rulebase.items():
          for regex_context in regex_group.get(src_lang, []) + regex_group.get("default", []):
              if True:
                  regex, context = regex_context
                  found_context = False
                  if context:
                      for c1 in context:
                        c1 = c1.lower()
                        for c2 in c1.split():
                          if c2 in sentence_set:
                              found_context = True
                              break
                        if found_context: break
                      if not found_context:
                          continue
                  for ent in regex.findall(sentence):
                      if not isinstance(ent, str):
                          continue
                      sentence2 = original_sentence
                      delta = 0
                      while True:
                        if ent not in sentence2:
                          break
                        else:
                          i = sentence2.index(ent)
                          j = i + len(ent)
                          if found_context:
                              len_sentence = len(sentence2)
                              left = sentence2[max(0, i - context_window) : i].lower()
                              right = sentence2[j : min(len_sentence, j + context_window)].lower()
                              found_context = False
                              for c in context:
                                c = c.lower()
                                if c in left or c in right:
                                    found_context = True
                                    break
                              if not found_context:
                                  continue
                              #ner[ent.strip()] = tag
                          sentence2 = sentence2[i+len(ent):]
                          all_ner.append((ent, delta+i, delta+j, tag))
                          delta += j
                          idx += 1
      for mention_tag in all_ner:
        ent, start, end, tag = mention_tag
        key = (ent, start, end)
        aHash = ner.get(key, {})
        aHash[tag] = aHash.get(tag, 0) + weight * (1.0 + len(ent)/100) # extra weight?
        ner[key] = aHash
      doc[ner_key] = ner 
    print (docs)
    return docs

  def hf_ner(self, hf_pipeline, src_lang, docs, chunks, stopwords=None, weight=1.5, text_key=None, ner_key=None, offset_key=None):
    """
    run the text through a Huggingface ner pipeline. 
    any tags found by this method will be weighted by the weight param
    TODO: use the predicted value of the logits to further weight prediction
    NOTE: we don't use results_arr = hf_pipeline([chunk[text_key] for chunk in chunks], grouped_entities=True)
    because grouped_entities does not properly group all entities as we do it below.
    """
    if stopwords is None:
      stopwords = set(stopwords.get(src_lang, []))
    if offset_key is None:
      offset_key = f'{src_lang}_offset'
    if ner_key is None:
      ner_key = f'{src_lang}_ner'
    if text_key is None:
      text_key = f'{src_lang}_text'
    results_arr = hf_pipeline([chunk[text_key] for chunk in chunks])
    results_arr2 = []
    offset = 0
    for chunk, results in zip(chunks, results_arr):
      text = chunk[text_key]
      _id = chunk['id']
      ner = docs[_id][ner_key] = docs[_id].get(ner_key,{})
      offset = chunk[offset_key]
      len_text= len(text)
      results = [ner_result for ner_result in results if ner_result['word'] not in ("[UNK]", "<unk>")]
      if not results: 
        results_arr2.append([])
        continue
      results2 = []
      if results[0]['start'] is not None: #TODO, test for the case where all the 'start' are '0'.
        results.sort(key=lambda a: a['start'])
      else:
        results.sort(key=lambda a: a['index'])
        i = 0
        for ner_result in results:
          ner_result['word'] = word = ner_result['word'].rstrip('@@')  
          ner_result['start'] = text.index(word, i)
          i = ner_result['start'] + 1
          ner_result['end'] = ner_result['start'] + len(word) 
        
      for ner_result in results:  
        start = ner_result['start']
        if not self.cjk_detect(text[ner_result['start']:ner_result['end']]):
              if text[start] not in self.strip_chars:
                for j in range(1, start):
                  if start - j == -1 or text[start-j] in self.strip_chars:
                    start = max(start -j, 0)
                    break
              end = ner_result['end']
              if end < len_text and text[end] != ' ':
                end += len(text[end:].split(' ', 1)[0])
        else:
              start = ner_result['start']
              end = ner_result['end']
        while text[start] in self.strip_chars:
          start += 1
          if start >= end: break
        end = start + len(text[start:end].strip(self.strip_chars))
        ner_result['word'] = text[start:end]
        ner_result['start'] = start+offset
        ner_result['end'] = end+offset
        if results2 and results2[-1]['end'] > ner_result['start']:
          continue
        results2.append(ner_result)
      results_arr2.append(results2)
    results_arr = results_arr2
    for chunk, results in zip(chunks, results_arr):
        _id = chunk['id']
        ner = docs[_id][ner_key]
        text = docs[_id][text_key]
        len_text = len(text)
        results = [ner_result for ner_result in results if ner_result['word'] not in ("[UNK]", "<unk>")]
        if not results: continue
        prev_word = [0,0]
        prev_label = None
        prev_word2 = ""
        for ner_result in results:
          start = ner_result['start']
          if start is None: 
            prev_word2 = ""
            continue
          end = ner_result['end']
          if text[start:end] != ner_result['word']:
            print ('offset mismatch', text[start:end], ner_result['word'])
          if "-" in ner_result['entity']:
            _, label = ner_result['entity'].split('-')
          else:
            label = ner_result['entity']
          label = label.upper()
          if label in ('ADDRESS', 'STREET_ADDRESS'): label = 'ADDRESS'
          elif label in ('PUBLIC_FIGURE',): label = 'PUBLIC_FIGURE'
          elif label in ('NAME', 'PER', 'PERSON'): label = 'PERSON'
          elif label in ('LOCATION', 'LOC', 'GPE'): label = 'LOC'
          elif label in ('ORGANIZATION', 'ORG'): label = 'ORG'
          elif label in ('AGE',): label = 'AGE'
          elif label in ('NORP',): label = 'NORP'
          elif label in ('BIO', 'SYMPTOM_AND_DISEASE', 'DISEASE' ): label = 'DISEASE'
          elif label in ('PATIENT_ID', 'GOVT_ID' ): label = 'ID'
          elif label in ('USER_ID', 'ID'): label = 'ID'
          elif label in ('MISC', ) and '@' in ner_result['word']: label = 'ID'
          else: label = 'MISC'
          if prev_label is not None:
              if not ner_result['entity'].startswith('B-') and label == prev_label and (prev_word[1] >= start - 5):
                prev_word[1] =  max(prev_word[1], end)
                prev_word2 = prev_word2 + " " + ner_result['word']
              else:
                if ner_result['entity'].startswith('B-'):
                  if prev_word[1] > start:
                    prev_word[1] = start
                if prev_word[0] != prev_word[1]:
                  ner_word = text[prev_word[0]:prev_word[1]]
                  #if ner_word != prev_word2:
                  #  print (ner_word, '**', prev_word2)
                  #ner_word.strip(self.strip_chars)
                  mention = (ner_word, prev_word[0], prev_word[1])
                  if ner_word and ner_word.lower() not in stopwords:
                    aHash = ner.get(mention, {})
                    aHash[prev_label] = aHash.get(prev_label, 0) + weight * (1.0 + len(ner_word)/100)
                    ner[mention] = aHash
                  prev_word = [start, end]
                  prev_word2 = ner_result['word']
          elif prev_label is None:
            prev_word = [start, end]
            prev_word2 = ner_result['word']
          prev_label = label
        
        if prev_label is not None and prev_word[0] != prev_word[1]:
            ner_word = text[prev_word[0]:prev_word[1]]
            #if ner_word != prev_word2:
            #  print (ner_word, '**', prev_word2)
            mention = (ner_word, prev_word[0], prev_word[1])
            if ner_word and ner_word.lower() not in stopwords:
                aHash = ner.get(mention, {})
                aHash[prev_label] = aHash.get(prev_label, 0) + weight * (1.0 + len(ner_word)/100)
                ner[mention] = aHash

  def add_chunks_span(self, chunks, new_mention, old_mention, label, coref, chunk2ner, mention2ref, ref2mention):
    """ add a span to the chunks sequence and update the various ref and NER hashes """
    if old_mention in chunk2ner:
      del chunk2ner[old_mention]
    if label:
      chunk2ner[new_mention] = label
    if old_mention in mention2ref:
      old_ref = mention2ref[old_mention]
      ref2mention[old_ref].remove(old_mention)
      if not ref2mention[old_ref]:
        del ref2mention[old_ref]
      del mention2ref[old_mention]
    if new_mention in mention2ref and coref != mention2ref[new_mention]:
      old_ref = mention2ref[new_mention]
      ref2mention[old_ref].remove(new_mention)
      if not ref2mention[old_ref]:
        del ref2mention[old_ref]
      del mention2ref[new_mention]
    if coref:
      mention2ref[new_mention] = coref
      lst = ref2mention.get(coref, [])
      if new_mention not in lst:
        ref2mention[coref] = lst + [new_mention]
    chunks.append(new_mention)

  def del_ner_coref(self, old_mention, chunk2ner, mention2ref, ref2mention):
    """ remove an old_mention from the various NER and ref hashes """
    if old_mention in chunk2ner:
      del chunk2ner[old_mention]
    if old_mention in mention2ref:
      old_ref = mention2ref[old_mention]
      ref2mention[old_ref].remove(old_mention)
      if not ref2mention[old_ref]:
        del ref2mention[old_ref]
      del mention2ref[old_mention]

  def spacy_ner_coref(self, docs, nlp, stopwords, spacy_weight, src_lang, extra_weight=1.0, text_key=None, ner_key=None, connector="_", pronouns=("who", "whom", "whose", "our", "ours", "you", "your", "my", "i", "me", "mine", "he", "she", "his", "her", "him", "hers", "it", "its", "they", "their", "theirs", "them", "we")):
    """ 
    Use the spacy English model to create chunks for English text
    and gather NER and coreference information
    """
    if not nlp:
      return
    if stopwords is None:
      stopwords = set(stopwords.get(src_lang, []))
    offset_key=f'{src_lang}_offset'
    if ner_key is None:
      ner_key = f'{src_lang}_ner'
    if text_key is None:
      text_key = f'{src_lang}_text'
    mention2ref_key = f'{src_lang}_mention2ref'
    ref2mention_key = f'{src_lang}_ref2mention'
    for dat in docs.values():
      chunk2ner = {}
      ref2mention = dat[ref2mention_key] =  dat.get(ref2mention_key,{})
      mention2ref = dat[mention2ref_key] =  dat.get(mention2ref_key,{})
      ner =  dat[ner_key] =  dat.get(ner_key,{})
      text = dat[text_key]
      doc = nlp(text)
      entities = list(doc.ents)
      # spacy is not as high accuracy as transformers, but we use the spacey neuralcoref model so we can get pronoun coreference groups
      # to be able to do proper gender swapping. 

      #store away NOUNs for potential label and coref reference
      #rule for promoting a noun span into one considered for further processing:
      # - length of the number of words > 2 or length of span > 2 and the span is all uppercase (for abbreviations)
      # coref candidates:
      # - create an abbreviation from noun phrases as a candidate coref.
      # - use either the last two words of a span as a candidate coref, or
      # - use the abbreviation as a candidate coref
      for entity in list(doc.noun_chunks) + list(doc.ents):
        chunk2ner[(entity.text, entity.start, entity.end)]= "NOUN"
        mention_lower = entity.text.lower()
        textArr = mention_lower.split()
        if len(textArr) > 2:
          short_span = " ".join(textArr[-2:])
          ref2mention[short_span] = ref2mention.get(short_span, []) + [(entity.text, entity.start, entity.end)]
          non_stopwords = [a for a in textArr if a not in self.stopwords_en]
          if len(non_stopwords) > 2:
            abrev = "".join([a[0] for a in non_stopwords])
            ref2mention[abrev] = ref2mention.get(abrev, []) + [(entity.text, entity.start, entity.end)]
        elif (len(entity.text) >=2 and entity.text == entity.text.upper()):
          ref2mention[entity.text.lower()] = ref2mention.get(entity.text.lower(), []) + [(entity.text, entity.start, entity.end)]

      #store away coref NOUNs for potential label and coref reference
      #same rule as above for promoting a noun span into one considered for further processing.
      for cl in list(doc._.coref_clusters):
        mentions = [(entity.text, entity.start, entity.end) for entity in cl.mentions]
        mentions.sort(key=lambda e: len(e[0]), reverse=True)
        textArr = mentions[0][0].lower().split()
        for key in mentions:
          chunk2ner[key]= "NOUN"
        for mention in mentions:
          mention_lower = mention[0].lower()
          textArr = mention_lower.split()
          if mention_lower not in self.stopwords_en:
            if len(textArr) > 1:
              short_span = " ".join(textArr[-2:])
            else:
              short_span = textArr[0]
            ref2mention[short_span] = ref2mention.get(short_span, []) + mentions
            non_stopwords = [a for a in textArr if a not in self.stopwords_en]
            if len(non_stopwords) > 2:
              abrev = "".join([a[0] for a in non_stopwords])
              ref2mention[abrev] = ref2mention.get(abrev, []) + mentions

      #cleanup the mention2ref, favoring large clusters with coref labels that are longer
      seen = {}
      corefs = [(a, list(set(b))) for a, b in ref2mention.items()]
      corefs.sort(key=lambda a: a[0].count(" ")+len(a[1]), reverse=True)
      for coref, spans in corefs:
        new_spans = []
        spans = list(set(spans))
        spans.sort(key=lambda a: a[1]+(1.0/(1.0+a[2]-a[1])))
        spans2 = []
        for span in spans:
          if spans2 and spans2[-1][1] >= span[1]:
            continue
          spans2.append(span)
        for span in spans2:
          if span in seen: continue
          seen[span] = 1
          new_spans.append(span)
        del ref2mention[coref]
        if new_spans:
          new_coref = [s[0] for s in new_spans]
          new_coref.sort(key=lambda a: len(a), reverse=True)
          ref2mention[new_coref[0].lower()] = list(set(list(ref2mention.get(new_coref[0].lower(), [])) + new_spans))

      mention2ref.clear()
      for a, b1 in ref2mention.items():
        for b in b1:
          mention2ref[b] = a

      # expand coref information by using the most common coref label in a cluster
      if True:
        for cl in list(doc._.coref_clusters):
          mentions = [(entity.text, entity.start, entity.end) for entity in cl.mentions]
          all_mentions = list(set(itertools.chain(*[ref2mention[mention2ref[mention]] for mention in mentions if mention in mention2ref])))
          corefs = [mention2ref[mention] for mention in mentions if mention in mention2ref]
          if corefs:
            coref = Counter(corefs).most_common()[0][0]
          else:
            coref = cl.main.text.lower()
          for mention in all_mentions:
            if mention not in chunk2ner:
              chunk2ner[mention] = 'NOUN'
            old_ref = mention2ref.get(mention)
            if old_ref and mention in ref2mention[old_ref]:
              ref2mention[old_ref].remove(mention)
              if not ref2mention[old_ref]:
                del ref2mention[old_ref]
            mention2ref[mention] = coref
            if mention not in ref2mention[coref]:
              ref2mention[coref].append(mention)

      #expand ner labels based on coref matches 
      for entity in list(doc.ents):
        mention = (entity.text, entity.start, entity.end)
        chunk2ner[mention]= entity.label_  
        if mention in mention2ref:
          coref = mention2ref[mention]
          for mention in ref2mention[coref]:
            chunk2ner[mention] = entity.label_  

      # overwrite all ner labels in the coref cluster to PERSON if there is a person pronoun
      if True:
        for cl in list(doc._.coref_clusters):
          cluster_text_list = set([m.text.lower() for m in cl.mentions])
          # I don't use "us" because that is sometimes the U.S.
          # TODO: fix to check for upper case only US as an exception
          if "you" in cluster_text_list or "your"  in cluster_text_list  or "yours"  in cluster_text_list  or  "we" in cluster_text_list  or 'i' in cluster_text_list  or 'my' in cluster_text_list  or 'mine' in cluster_text_list or 'me' in cluster_text_list or 'he' in cluster_text_list or "she" in cluster_text_list or "his" in cluster_text_list or "her" in cluster_text_list or "him" in cluster_text_list or "hers" in cluster_text_list:
            label = "PERSON"
            for m in cl.mentions:
              chunk2ner[(m.text, m.start, m.end)] = label

      # propogate the ner label to everything in the same coref group
      for coref, seq in ref2mention.items():
        labels = [chunk2ner[mention]  for mention in seq if mention in chunk2ner and chunk2ner[mention] != 'NOUN']
        if labels:
          label = Counter(labels).most_common()[0][0]
          for mention in seq:
            if mention in chunk2ner and  not (label == 'PERSON' or chunk2ner[mention] == 'PUBLIC_FIGURE'): chunk2ner[mention] = label

      #sort the chunks into order
      chunks = list(chunk2ner.items())
      chunks.sort(key=lambda a: a[0][1]+(1.0/(1.0+a[0][2]-a[0][1])))
      chunks2 = []

      #clear duplicates and subsumed mentions 
      for mention, label in chunks:
        if not chunks2 or (chunks2[-1][2] <= mention[1]):
          if not chunks2 or chunks2[-1][2] < mention[1]: 
            self.add_chunks_span(chunks2, (doc[0 if not chunks2 else chunks2[-1][2]: mention[1]].text, 0 if not chunks2 else chunks2[-1][2], mention[1]), \
                                 None, None, None, chunk2ner, mention2ref, ref2mention)
          self.add_chunks_span(chunks2, mention, None, label, mention2ref.get(mention), chunk2ner, mention2ref, ref2mention)
        elif chunks2[-1][2] > mention[1] and chunks2[-1][1] <= mention[1]:
          if chunk2ner.get(chunks2[-1]) not in (None, '', 'NOUN'):
            self.del_ner_coref(mention, chunk2ner, mention2ref, ref2mention)
            continue
          elif label in  (None, '', 'NOUN'):
            self.del_ner_coref(mention, chunk2ner, mention2ref, ref2mention)
            continue
          old_mention = chunks2.pop()
          oldSpan = old_mention[0]
          oldLabel = chunk2ner.get(old_mention)
          oldAnaphore = mention2ref.get(old_mention)
          sArr = oldSpan.split(mention[0], 1)
          self.del_ner_coref(old_mention, chunk2ner, mention2ref, ref2mention)
          s0 = sArr[0].strip()
          if s0:
            self.add_chunks_span(chunks2, (s0, old_mention[1], mention[1]), None, \
                                 oldLabel if s0 in pronouns or (len(s0) > 1 and s0 not in self.stopwords_en) else None, oldAnaphore  if s0 in pronouns or (len(s0) > 1 and s0 not in self.stopwords_en) else None, \
                                 chunk2ner, mention2ref, ref2mention)
          self.add_chunks_span(chunks2,  mention, None, label, oldAnaphore if not mention2ref.get(mention) else mention2ref.get(mention), chunk2ner, mention2ref, ref2mention)
          if len(sArr) > 1:
            s1 = sArr[1].strip()
            if s1:
              self.add_chunks_span(chunks2, (s1, mention[2], old_mention[2]), None,  \
                                   oldLabel if s1 in pronouns or (len(s1) > 1 and s1 not in self.stopwords_en) else None, oldAnaphore  if s1 in pronouns or (len(s1) > 1 and s1 not in self.stopwords_en) else None, \
                                   chunk2ner, mention2ref, ref2mention)
      len_doc = len(doc)
      if chunks2[-1][2] < len_doc:
        self.add_chunks_span(chunks2, (doc[chunks2[-1][2]:].text, chunks2[-1][2], len_doc), None, None, None, chunk2ner, mention2ref, ref2mention)

      #reset the indexes for chunks to be per character index.
      i = 0
      for spanIdx, mention in enumerate(chunks2):
          label = chunk2ner.get(mention)
          if label in ('WORK_OF_ART', 'NOUN', None): continue
          if label in ('GPE', 'FAC'): label = 'LOC'
          if label in ('PERSON', 'PUBLIC_FUGRE'):
            coref = ref2mention.get(mention2ref.get(mention), [])
            if "he" in coref or "He" in coref or "him" in coref or "Him" in coref or "his" in coref or "His" in coref or "Mr." in coref or "Mr" in coref or "mr" in coref or "mr." in coref:
              gender = "he"
            elif "she" in coref or "She" in coref or "her" in coref or "Her" in coref or "hers" in coref or "Hers" in coref or "Miss" in coref or "miss" in coref or  "Mrs." in coref or "Mrs" in coref or "mrs" in coref or "mrs." in coref or "Ms." in coref or "Ms" in coref or "ms" in coref or "ms." in coref:
              gender = "she"
            else:
              gender = random.choice(["she", "he", "they"])
            #TODO - save gender away so we can do better name anonymization

          ner_word = mention[0]
          if ner_word and ner_word.lower() not in stopwords:
              if not self.cjk_detect(ner_word):
                if ner_word not in text: continue
                i += text[i:].index(ner_word)
                ner_word = text[i:].split(" ", 1)[0]
              ner_word = ner_word.strip(self.strip_chars)
              if ner_word.lower() not in stopwords:
                mention = (ner_word, i, i+len(ner_word))
                aHash = ner.get(mention, {})
                aHash[label] = aHash.get(label, 0) + spacy_weight * (1.0 + len(ner_word)/100) * extra_weight
                ner[mention] = aHash
      """
        self.del_ner_coref(mention, chunk2ner, mention2ref, ref2mention)
        new_word = mention[0]
        len_new_word = len(new_word)
        self.add_chunks_span(chunks, (new_word, 0 if not chunks else chunks[-1][2]+1,  len_new_word if not chunks else chunks[-1][2]+1+len_new_word), None, label, coref, chunk2ner, mention2ref, ref2mention)
      text = " ".join([c[0] for c in chunks])
      #print (chunk2ner)
      #print (mention2ref)
      print (ref2mention)
      for mention, tag in chunk2ner.items():
        if tag in ('WORK_OF_ART', 'NOUN'): continue
        if tag in ('GPE', 'FAC'): tag = 'LOC'
        aHash = ner.get(mention, {})
        ner_word= mention[0]
        aHash[tag] = aHash.get(tag, 0) +  spacy_weight * (1.0 + len(ner_word)/100) * extra_weight
        ner[mention] = aHash
      """
      print (ner)
    return docs #text, chunks, chunk2ner, mention2ref, ref2mention

  def spacy_ner(self, docs, nlp, stopwords, spacy_weight, src_lang, extra_weight=1.0, text_key=None, ner_key=None):
      """ 
      Use the spacy models to create mentions w/ NER
      """
      if neuralcoref is not None:
        return self.spacy_ner_coref(docs, nlp, stopwords, spacy_weight, src_lang, extra_weight=extra_weight, text_key=text_key, ner_key=ner_key)
      else:
        if not nlp:
          return
        if stopwords is None:
          stopwords = set(stopwords.get(src_lang, []))
        offset_key=f'{src_lang}_offset'
        if ner_key is None:
          ner_key = f'{src_lang}_ner'
        if text_key is None:
          text_key = f'{src_lang}_text'
        for dat in docs.values():
          ner =  dat[ner_key] =  dat.get(ner_key,{})
          text = dat[text_key]
          doc = nlp(text)
          entities = list(doc.ents)
          ents = [(entity.text, entity.label_ if (entity.label_ in ('PERSON', 'GPE', 'ORG', 'NORP') and 'http:' not in entity.text) else 'MISC') for entity in entities]
          i = 0
          for ner_word, label in ents: 
            ner_word = ner_word.strip(self.strip_chars)
            if ner_word and ner_word.lower() not in stopwords:
              if not self.cjk_detect(ner_word):
                if ner_word not in text: continue
                i += text[i:].index(ner_word)
                ner_word = text[i:].split(" ", 1)[0]
              ner_word = ner_word.strip(self.strip_chars)
              if ner_word.lower() not in stopwords:
                mention = (ner_word, i, i+len(ner_word))
                aHash = ner.get(mention, {})
                aHash[label] = aHash.get(label, 0) + spacy_weight * (1.0 + len(ner_word)/100) * extra_weight
                ner[mention] = aHash

  def trim_to_prefer_person(self, docs, chunks, prob=100):
      # downsample to mostly docs with mentions of people, id/email
      # if there were no ner set, then don't downsample the doc    
      len_docs = len(docs)
      do_ids = []
      for _id, doc in docs.items():
        if not any(key for key in doc if key.endswith('_ner')):
          do_ids.append(_id)
          continue
        found_ner = False
        for key in list(doc.keys()):
          if doc.get('has_person'):
            do_ids.append(_id)
            break
          if "_ner" in key:
            if not found_ner:
              found_ner = doc[key] != {}
            ner =  doc[key] 
            for aHash in ner.values():
              if type(aHash) is dict and 'PUBLIC_FIGURE' in aHash or 'PERSON' in aHash or 'ID' in aHash: 
                doc['has_person'] = True
                do_ids.append(_id)
                break
        if doc.get('has_person'):
            do_ids.append(_id)
        elif not doc.get('has_person') and random.randint(0, prob) == 0:
            do_ids.append(_id)
      do_ids = set(do_ids)
      chunks2 = [chunk for chunk in chunks if chunk['id'] in do_ids]
      docs2 = dict([(doc['id'], doc) for doc in docs.values() if doc['id'] in do_ids])
      if len(docs2) == 0 or len_docs == len(docs2):
        return docs, chunks
      print ('trim_to_prefer_person', (len_docs-len(docs2))/len_docs)
      return docs2, chunks2


  def collapse_ner(self, docs, ner_key, text_key):
    for doc in docs.values():
      text = doc.get(text_key, "")
      chunk2ner = doc.get(ner_key, {})
      chunks = list(chunk2ner.items())
      chunks.sort(key=lambda a: a[0][1]+(1.0/(1.0+a[0][2]-a[0][1])))
      chunks2 = []
      
      for mention, labelsHash in chunks:
        mention = list(mention)
        if not chunks2:
          chunks2.append([mention[0], mention[1], mention[2], labelsHash])
        # completely or mostly subsumed
        elif chunks2[-1][2] > mention[2] or chunks2[-1][2] - mention[1] > 3:
          prev_ent, prev_start, prev_end, prev_labelsHash = chunks2[-1]
          for tag in labelsHash:
            prev_labelsHash[tag]  = prev_labelsHash.get(tag, 0) + labelsHash.get(tag, 0)
          chunks2[-1][2] = mention[2]
          print (chunks2[-1], text)
          chunks2[-1][0] = text[chunks2[-1][1]:chunks2[-1][2]]
        elif chunks2[-1][2] < mention[1]:
          chunks2.append([mention[0], mention[1], mention[2], labelsHash])
        # partially subsumed
        else:
          if mention[2] - mention[1] > chunks2[-1][2] - chunks2[-1][1]:
              chunks2[-1][2] = mention[1] -1
              chunks2[-1][0] = text[chunks2[-1][1]:chunks2[-1][2]]
          else:
              mention[1] = chunks2[-1][2] + 1
              mention[0] = text[mention[1]:mention[2]]
          chunks2.append([mention[0], mention[1], mention[2], labelsHash])

      ner = {}
      for ent, start, end, labelsHash in chunks2:
        ent = ent.strip(self.strip_chars)
        if ent:
          mention = (ent, start, start + len(ent))
          ner[mention] = labelsHash
      doc[ner_key] = ner
    return docs

  #TODO - refactor this method into parts
  def process_ner_chunks_with_trans(self, 
                          src_lang, 
                          docs, 
                          chunks, 
                          target_lang=None,
                          do_spacy = True,
                          do_hf_ner = True,
                          do_ontology = True,
                          do_backtrans=False,
                          do_augment=False,
                          do_anonymization=False,
                          do_regex = True,
                          do_cleanup=True,
                          batch_size = 5, 
                          batch_window=70,
                          ontology_weight=0.9,
                          spacy_weight=1.25,
                          hf_ner_weight=1.0,
                          regex_weight=2.0,
                          backtrans_weight=0.9,
                          do_docs_trim=False,
                          aug_scope={'ADDRESS', 'ORG', 'PERSON', 'LOC', 'ID'}, #TODO, public figure, age, norp and disease
                          anon_scope={'PERSON', 'ID'},):
    if do_augment and do_backtrans:
      assert False, "Only augment or backtrans can be performed at a time, not both"
    if do_augment and do_anonymization:
      assert False, "Only augment or anonymization can be performed at a time, not both"
    if target_lang is None:
        target_lang = src_lang
    if (do_augment or do_anonymization) and target_lang != src_lang:
      if target_lang not in ("eu", "ca") and target_lang not in faker_map:
        faker_target_lang = random.choice(self.faker_en_list)
      else: 
        faker_lang_list = faker_map["es" if target_lang in ("eu", "ca") else target_lang]                      
        faker_target_lang = Faker(random.choice(faker_lang_list))
        faker_target_lang.add_provider(person)
        faker_target_lang.add_provider(ssn)
        faker_target_lang.add_provider(address)
        faker_target_lang.add_provider(company)
  
      if src_lang not in ("eu", "ca") and src_lang not in faker_map:
        faker_src_lang = random.choice(self.faker_en_list)
      else: 
        faker_lang_list = faker_map["es" if src_lang in ("eu", "ca") else src_lang]                      
        faker_src_lang = Faker(random.choice(faker_lang_list))
        faker_src_lang.add_provider(person)
        faker_src_lang.add_provider(ssn)
        faker_src_lang.add_provider(address)
        faker_src_lang.add_provider(company)

      faker_en = random.choice(self.faker_en_list)

    else:
      faker_target_lang = None
      faker_en = None
    stopwords1 = set(stopwords[src_lang])
    stopwords2 = set(stopwords[target_lang])

    #init spacy pipeline
    spacy_nlp = None
    if do_spacy:
      if target_lang == 'en':
        spacy_nlp = self.en_spacy_nlp
      elif target_lang == 'zh':
        try:
          spacy_nlp = spacy.load('zh_core_web_sm')
        except:
          pass
      elif target_lang == 'pt':
        spacy_nlp = spacy.load('pt_core_news_sm')
      elif target_lang == 'fr':
        spacy_nlp = spacy.load('fr_core_news_sm')
      elif target_lang == 'ca':
        try:
          spacy_nlp = spacy.load('ca_core_news_sm')
        except:
          pass
    model = None
    ner_pipelines = []

    # init hf ner pipelines
    if do_hf_ner:
      for model_name, model_cls, hf_ner_weight2 in self.hf_ner_model_map.get(target_lang, []):
        if model_name not in self.ner_model_name2pipelines:
          print ("setting") 
          try:
            model = model_cls.from_pretrained(model_name).half().eval().cuda()
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, device=0)
            self.ner_model_name2pipelines[model_name] = ner_pipeline
          except:
            try:
              ner_pipeline = pipeline("ner",  model=model_name, tokenizer=(model_name, {"use_fast": True},), device=0)
              self.ner_model_name2pipelines[model_name] = ner_pipeline
            except:
              ner_pipeline = pipeline("ner",  model=model_name, tokenizer=(model_name, {"use_fast": True},), framework="tf", device=0)
              self.ner_model_name2pipelines[model_name] = ner_pipeline
        ner_pipelines.append((self.ner_model_name2pipelines[model_name], hf_ner_weight2))
    target_is_cjk = target_lang in ('zh', 'ko', 'ja')
    src_is_cjk = src_lang in ('zh', 'ko', 'ja')
    if do_augment:
      target_text_key = f'{target_lang}_text_aug'
      target_ner_key =  f'{target_lang}_ner_aug'
      target_offset_key = f'{target_lang}_offset_aug'
      target_src_sim_key = f'{src_lang}_2_{target_lang}_sim_aug'
    else:
      target_text_key = f'{target_lang}_text'
      target_ner_key = f'{target_lang}_ner'
      target_offset_key = f'{target_lang}_offset'
      target_src_sim_key = f'{src_lang}_2_{target_lang}_sim'

    # do operations in the target_lang
    if target_lang == src_lang:
      backtrans_weight = 1.0
      do_backtrans = False
      
    elif target_lang != src_lang:
        #translate from src_lang to target_lang and do ner in target_lang.  translation also acts as an error check and additional ner. 
        # we check to see if the already tagged items in src lang should have scores for tags increased or are common words in target lang and should not be tagged. 
        # we also add new labels for items that are already tagged in src_lang.        
        if src_is_cjk:
            sep = ""
        else:
            sep = " "

        if src_is_cjk or target_is_cjk:
            lbracket = "[["
            rbracket = "]]"
        else:
            lbracket = "["
            rbracket = "]"

        for chunk in chunks:
          text = chunk[f'{src_lang}_text'].replace("(", "{").replace(")", "}")
          _id = chunk['id']
          offset = chunk[f'{src_lang}_offset']
          doc = docs[_id]
          offset_end = offset + len(text)
          if f'{src_lang}_items' not in doc:
            doc[f'{src_lang}_items'] = list(doc.get(f'{src_lang}_ner', {}).keys())
            doc[f'{src_lang}_items'].sort(key=lambda a: a[1]) # sort by order in sentence
          i = 0
          for idx, key in enumerate(doc[f'{src_lang}_items']):
            if key[1] < offset:
              continue
            if key[2] > offset_end:
              break
            if len(key[0]) < 4 and not self.cjk_detect(key[0]):
              if " "+key[0]+" " in text[i:]:
                j = text.index(" "+key[0]+" ", i)
                text = text[:j]+(text[j:].replace(" "+key[0]+" ", f"  **{idx}**  ", 1))
                i = j
            else:
              if key[0] in text[i:]:
                j = text.index(key[0], i)
                text = text[:j]+(text[j:].replace(key[0], f"  **{idx}**  ", 1))
                i = j
          chunk[f'{src_lang}_tmp_text'] = text

        src_items_sorted = list(enumerate(doc[f'{src_lang}_items']))
        src_items_sorted.sort(key=lambda a: len(a[1][0]), reverse=True)
        for chunk in chunks:
          text = chunk[f'{src_lang}_tmp_text']
          _id = chunk['id']
          doc = docs[_id]
          for idx, key in src_items_sorted:
            if len(key[0]) < 5 and not self.cjk_detect(key[0]):
              text = text.replace(" "+key[0]+" ", f"  **{idx}**  ")
            else:
              text = text.replace(key[0], f" **{idx}** ")
          chunk[f'{src_lang}_tmp_text'] = text

        for doc in docs.values():
          # do augmentation in src_lang, and then translate to target_lang. 
          if do_augment and faker_target_lang is not None and faker_en is not None:
            context = doc[f'{src_lang}_aug_context'] = doc.get(f'{src_lang}_aug_context', {})
            ner = doc.get(f'{src_lang}_ner', {})
            src_items_sorted = list(enumerate(doc[f'{src_lang}_items']))
            src_items_sorted.sort(key=lambda a: len(a[1][0]), reverse=True)

            for idx, key in src_items_sorted:
              if key not in ner: continue
              ent = key[0]
              tag = ner[key]
              if ent in context: continue
              #TODO - do proper gender based aug and gender swap
              if 'PERSON' in aug_scope and tag == 'PERSON':
                context[ent] = context.get(ent, faker_en.first_name() + " " + random.choice(bantu_surnames) if " " in ent and target_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh",) else \
                                      random.choice(bantu_surnames) if target_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh",) else \
                                      random.choice(vietnamese_surnames) + " " + random.choice(vietnamese_firstnames) if " " in ent and target_lang =="vi" else \
                                      random.choice(vietnamese_surnames) if  target_lang == "vi" else \
                                      faker_en.first_name() + " " + random.choice(bengali_surnames) if " " in ent and target_lang =="bn" else \
                                      random.choice(bengali_surnames) if target_lang == "bn" else \
                                      random.choice(urdu_firstnames)  + " " + random.choice(urdu_surnames) if " " in ent and target_lang =="ur" else \
                                      random.choice(urdu_surnames) if target_lang == "ur" else \
                                      faker_target_lang.name() if " " in ent else \
                                      faker_target_lang.first_name() )
                
              if 'LOC' in aug_scope and tag == 'LOC':
                context[ent] = context.get(ent, faker_en.country() if  target_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh", "bn", "ur", "vi", "eu") else \
                                      faker_target_lang.state() if target_lang != 'zh' else \
                                      faker_target_lang.province() if  target_lang == 'zh' else 
                                      ent)
              if 'ORG' in aug_scope and tag == 'ORG':
                try:
                  context[ent] = context.get(ent, faker_target_lang.company())
                except:
                  context[ent] = context.get(ent, faker_en.company())

              if 'ID' in aug_scope and tag == 'ID':
                context[ent] = context.get(ent, str(random.randrange(10000000,999999999)) if target_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh", "bn", "ur", "vi", "eu")  else \
                                      faker_target_lang.ssn())
                
              if 'ADDRESS' in aug_scope and tag == 'ADDRESS':
                context[ent] = context.get(ent, faker_en.address() if target_lang not in ("yo", "sw","sn", "st", "ig", "ny", "xh", "bn", "ur", "vi", "eu") else \
                                      faker_target_lang.address() )
              
              if tag in  ('PESON', 'ORG') and tag in aug_scope :
                src_first, src_last = None, None
                target_first, target_last = None, None
                if src_lang in ("ja", "ko", "zh") and len(ent) > 1:
                  src_first, src_last = ent[0], ent[-1]
                elif " " in ent:
                  src_first, src_last =  ent.split()[0], ent.split()[-1]
                if target_lang in ("ja", "ko", "zh"):
                  target_first, target_last = context[ent][0], context[ent][-1]
                elif " " in context[ent]:
                  target_first, target_last = context[ent].split()[0], context[ent].split()[-1]
                if src_first and (src_lang  in ("ja", "ko", "zh") or len(src_first) > 3) and src_first not in context:
                  context[src_first] = target_first
                if src_last and (src_lang  in ("ja", "ko", "zh") or len(src_last) > 3) and src_last not in context:
                  context[src_last] = target_last
            print (context)
        
        for chunk in chunks:
          context = doc[f'{src_lang}_aug_context'] = doc.get(f'{src_lang}_aug_context', {})
          text = chunk[f'{src_lang}_tmp_text']
          _id = chunk['id']
          doc = docs[_id]
          for idx, key in enumerate(doc[f'{src_lang}_items']):
            if do_augment:
              ent = context.get(key[0], key[0])
            else:
              ent = key[0]
            text = text.replace(f" **{idx}** ", f" {idx} {lbracket} {ent} {rbracket}")
          chunk[f'{src_lang}_tmp_text'] = text.replace("  ", " ")
   
        #print ('*****', chunks2)
        chunks2 = [chunk[f'{src_lang}_tmp_text'] for chunk in chunks]
        text2 = self.do_translations(chunks2, src_lang=src_lang, target_lang=target_lang, batch_size=batch_size)
        for chunk, trans_text in zip(chunks, text2):
          #langid check
          try:
            lang =  langid.classify(trans_text)[0]
          except:
            lang = target_lang
          if lang == target_lang:
            chunk[target_text_key] = trans_text.lstrip(" .").replace(rbracket, "]").replace(lbracket, "[").replace("}", ")").replace("{", "(")
          else:
            chunk[target_text_key] = " . . . "

        all_embed = self.labse.encode(chunks2, convert_to_tensor=True)
        all_trans_embed = self.labse.encode([chunk[target_text_key] for chunk in chunks], convert_to_tensor=True)
        similarity = cosine_similarity(all_embed, all_trans_embed, dim=1)
        for chunk, sim_score in zip(chunks, similarity):
          trans_text = chunk[target_text_key]
          sim_score = sim_score.item()
          print (sim_score, '**', trans_text, '**', chunk[f'{src_lang}_tmp_text'])
          _id = chunk['id']
          doc = docs[_id]
          if (do_augment and sim_score < 0.5) or (not do_augment and sim_score < 0.75):
            trans_text = chunk[target_text_key] = " . . . "
            if doc.get(target_text_key, ""):
              chunk[target_offset_key] = len(doc.get(target_text_key, "")) + 1
            else:
              chunk[target_offset_key] = 0
            doc[target_text_key] = (doc.get(target_text_key, "") + " " + trans_text).strip()
            chunk[target_src_sim_key] = 0.0
            continue
          chunk[target_src_sim_key] = sim_score
          len_items = len(doc[f'{src_lang}_items'])
          doc[f'{target_lang}_2_{src_lang}_ner'] = doc.get(f'{target_lang}_2_{src_lang}_ner', {})
          while "[" in trans_text:
            before, after = trans_text.split("[",1)
            before = before.strip()
            after = after.strip()
            before_arr = before.split()
            if "]" not in after or not before_arr:
              trans_text = before + sep + after
              continue
            idx = before_arr[-1]
            ent, after = after.split("]", 1)
            ent = ent.strip()

            if True:
              try:
                idx = int(idx)
              except:
                idx = None
              if idx is not None and idx < len_items:
                before = " ".join(before_arr[:-1])
                key = doc[f'{src_lang}_items'][idx]
                ent_lower = ent.lower()
                if ent_lower in stopwords2: 
                  #reduce weight of target labels if this is translated into an en stopword
                  if key in doc[f'{src_lang}_ner']: 
                    aHash = doc[f'{src_lang}_ner'][key]
                    for key in list(aHash.keys()):
                      aHash[key] /= 2.0
                else:
                  vals = list(doc[f'{src_lang}_ner'][key].keys())
                  ent = ent.strip(self.strip_chars)
                  doc[f'{target_lang}_2_{src_lang}_ner'][ent] = idx
            else: # except:
              pass
            trans_text = before + " " + ent + " " + after
          trans_text = chunk[target_text_key] = trans_text.replace("  ", " ").strip() 
          if doc.get(target_text_key, ""):
            chunk[target_offset_key] = len(doc.get(target_text_key, "")) + 1
          else:
            chunk[target_offset_key] = 0
          doc[target_text_key] = (doc.get(target_text_key, "") + " " + trans_text).strip()
    
    if do_regex:
      docs = self.apply_regex_ner(target_lang, docs=docs, weight=regex_weight, text_key=target_text_key, ner_key=target_ner_key)

    if False: # do_ontology and self.ontology_manager is not None:
        # ontology - context independent - there are some bugs in disease detection which needs to be fixed so we will skip for now
        for doc in docs.values():
          doc[target_ner_key] = ner = doc.get(target_ner_key, {})
          if target_lang == 'en':
            chunk2ner = self.ontology_manager.tokenize(doc[target_text_key])['chunk2ner']
            onto_items = []
            for c, label in chunk2ner.items():
              ner_word  = c[0].replace(" ", "").replace("_", "").replace("_", "") if self.cjk_detect(c[0]) else c[0].replace("_", " ").replace("_", " ").rstrip(self.strip_chars)
              if ner_word.lower() not in stopwords2:
                if not self.cjk_detect(ner_word) and label in ('PERSON', 'PUBLIC_FIGURE', 'ORG') and " " not in ner_word: continue
                onto_items.append(((ner_word, c[1], c[1] + len(ner_word)), label))
            for ner_mention, label in list(set(onto_items)):
                aHash = ner.get(ner_mention, {})
                aHash[label] = aHash.get(label, 0) + ontology_weight * (1.0 + len(ner_mention[0])/100) * backtrans_weight
                ner[ner_mention] = aHash

    if do_spacy:
        if spacy_nlp:
          # spacy
          self.spacy_ner(docs, spacy_nlp, stopwords2, spacy_weight, target_lang, extra_weight=backtrans_weight, text_key=target_text_key, ner_key=target_ner_key)

    if do_hf_ner:
        # transformer
        for ner_pipeline, hf_ner_weight2 in ner_pipelines:
          for a_batch in self.batch(chunks, batch_size):
            self.hf_ner(ner_pipeline, target_lang, docs, a_batch, stopwords=stopwords2, weight=hf_ner_weight*backtrans_weight*hf_ner_weight2, text_key=target_text_key, ner_key=target_ner_key, offset_key=target_offset_key)
    
    if do_cleanup:
        #do some cleanups. we don't want any ner that are just short numbers (but what about govt id?), stopwords or single characters.
        for _id, doc in docs.items():
          ner =  doc[target_ner_key] 
          for key in list(doc[target_ner_key].keys()):
            ner_word = key[0]
            try:
              if len(ner_word) < 4 and float(ner_word):
                #print ("deleting ", ner_word)
                del doc[target_ner_key][key]
                continue
            except:
              pass
            if ner_word.lower() in stopwords2 or (not self.cjk_detect(ner_word) and len(ner_word) <= 1):
              #print ("deleting ", ner_word)
              del doc[target_ner_key][key]

    #increase weight of src ner items if the target translations indicate it's an NER
    if target_lang != src_lang and not do_augment:
          for doc in docs.values():
            ner =  doc[f'{target_lang}_ner'] 
            target2src_ner = doc.get(f'{target_lang}_2_{src_lang}_ner', {})
            for ent, idx in target2src_ner.items():
              key = doc[f'{src_lang}_items'][idx]
              #NOTE that this is an unordered match
              ner_match = [key2 for key2 in ner if ent == key2[0]]
              if not ner_match and len(ent) > 3:
                ner_match = [key2 for key2 in ner if (ent in key2[0] or (len(key2[0]) > 3 and key2[0] in ent))]
              if ner_match:
                if key in doc[f'{src_lang}_ner']: 
                  aHash = doc[f'{src_lang}_ner'][key]
                  all_labels = []
                  for key2 in ner_match:
                    all_labels.extend(list(ner[key2].keys()))
                  all_labels = set(all_labels)
                  found = False
                  for label in list(aHash.keys()):
                    if label in all_labels or 'MISC' in all_labels:
                      aHash[label] *= 1.1
                      print ('increasing ', key, label, aHash[label])
                      found = True
                  if not found:
                    print ('not found', key, all_labels)

    if do_docs_trim:
      docs, chunks = self.trim_to_prefer_person(docs, chunks)
    
    docs = self.collapse_ner(docs, target_ner_key, target_text_key)
    
    if do_backtrans and target_lang != src_lang and not do_augment:
        #TBD: we could run the augmented text back to the original sentence create additional augmented data.

        #backtrans from src_lang to target_lang back to src_lang allows us to catch more NER using target lang NER tools.
        #then we tag in target_lang those items we haven't already found, and tranlsate back to match the original text.
        #NOTE: We do not modify the original text, but only use backtrans to do NER tagging and other analysis. 
        if target_is_cjk:
              sep = ""
        else:
              sep = " "
        if target_is_cjk: 
              lbracket = "[["
              rbracket = "]]"
        else:
              lbracket = "["
              rbracket = "]"
        for chunk in chunks:
          _id = chunk['id']
          text = chunk[f'{target_lang}_text'].replace("[", "{").replace("(", "{").replace(")", "}").replace("]", "}")
          offset = chunk[f'{target_lang}_offset']
          doc = docs[_id]
          offset_end = offset + len(text)
          if f'{target_lang}_items' not in doc:
            doc[f'{target_lang}_items'] = list(doc.get(f'{target_lang}_ner', {}).keys())
            doc[f'{target_lang}_items'].sort(key=lambda a: a[1])
          i = 0
          for idx, key in enumerate(doc[f'{target_lang}_items']):
            if key[1] < offset:
              continue
            if key[2] > offset_end:
              break
            if len(key[0]) < 5 and not self.cjk_detect(key[0]):
              if " "+key[0]+" " in text[i:]:
                j = text.index(" "+key[0]+" ", i)
                text = text[:j]+(text[j:].replace(" "+key[0]+" ", f"  **{idx}**  ", 1))
                i = j
            else:
              if key[0] in text[i:]:
                j = text.index(key[0], i)
                text = text[:j]+(text[j:].replace(key[0], f"  **{idx}**  ", 1))
                i = j
          chunk[f'{target_lang}_tmp_text'] = text

        target_items_sorted = list(enumerate(doc[f'{target_lang}_items']))
        target_items_sorted.sort(key=lambda a: len(a[1][0]), reverse=True)
        for chunk in chunks:
          text = chunk[f'{target_lang}_tmp_text']
          _id = chunk['id']
          doc = docs[_id]
          for idx, key in target_items_sorted:
            if len(key[0]) < 5 and not self.cjk_detect(key[0]):
              text = text.replace(" "+key[0]+" ", f"  **{idx}**  ")
            else:
              text = text.replace(key[0], f" **{idx}** ")
          chunk[f'{target_lang}_tmp_text'] = text

        for chunk in chunks:
          text = chunk[f'{target_lang}_tmp_text']
          _id = chunk['id']
          doc = docs[_id]
          for idx, key in enumerate(doc[f'{target_lang}_items']):
            text = text.replace(f" **{idx}** ", f" {idx} {lbracket} {key[0]} {rbracket}")
          chunk[f'{target_lang}_tmp_text'] = text.replace("  ", " ")

        backtrans_text = self.do_translations([chunk[f'{target_lang}_tmp_text'] for chunk in chunks], src_lang=target_lang, target_lang=src_lang, batch_size=batch_size)
        for chunk, trans_text in zip(chunks, backtrans_text):
          #langid check
          try:
            lang =  langid.classify(trans_text)[0]
          except:
            lang = target_lang
          if lang == target_lang:
            chunk[f'{src_lang}_text_backtrans_from_{target_lang}'] = trans_text.lstrip(" .").replace(rbracket, "]").replace(lbracket, "[").replace("}", ")").replace("{", "(")
          else:
            chunk[f'{src_lang}_text_backtrans_from_{target_lang}'] = " . . . "
        
        #TODO: do similiarty test?
        for chunk, trans_text in zip(chunks, backtrans_text):
          _id = chunk['id']
          doc = docs[_id]
          orig_text = chunk[f'{src_lang}_text']
          trans_text = chunk[f'{src_lang}_text_backtrans_from_{target_lang}'] 
          items = doc[f'{target_lang}_items']
          len_items = len(items)
          doc[f'{src_lang}_2_{target_lang}_backtrans_ner'] = ner = doc.get(f'{src_lang}_2_{target_lang}_backtrans_ner', {})
          pos = 0
          blocks, score =  self.get_aligned_text(orig_text, trans_text, src_lang)
          prev_t = None
          prev_o = None
          ner_word = ""
          ent2 = ""
          idx = None
          for o, t, _ in blocks:
            before = after = ""
            if "]" in t:
              ner_word = ""
              ent2 = ""
              t_arr = t.split("]")
              before = sep.join(t_arr[-1:])
              after = t_arr[-1]
              before = before.strip()
              if not before: 
                continue
              idx = before.split()[-1]
              try:
                idx = int(idx)
              except:
                idx = None
                if prev_t and prev_t.strip():
                  idx = prev_t.strip().split()[-1]
                  try:
                    idx = int(idx)
                  except:
                    idx = None
                    pass  
            if idx is not None and idx < len_items:
              ner_word += o
              if after:
                ent2 = after.split("[", 1)[0]
              else:
                ent2 += t.split("[", 1)[0]
              if "[" in t:
                key = items[idx]
                if key in ner:
                  ner_word = ner_word.strip(self.strip_chars)
                  ent2 = ent2.strip(self.strip_chars)
                  if ent2 in ner_word:
                    ner_word = ent2
                  else:
                    if src_is_cjk:
                      ent2arr = list(ent2)
                      ner_wordarr = list(ner_word)
                    else:
                      ent2arr = ent2.split()
                      ner_wordarr = ner_word.split()
                    len_ent2arr = len(ent2arr)
                    found=False
                    if  len_ent2arr > 3:
                      ent3 = sep.join(ent2arr[:3])
                      if ent3 in new_word:
                        new_word = ner_word[ner_word.index(ent3):]
                        found=True
                    if not found:
                      if len_ent2arr < len(new_wordarr):
                        new_word = sep.join(new_wordarr[-len_ent2arr:])
                  if ner_word and ner_word.lower() not in stopwords1: 
                    i = orig_text[pos:].index(ner_word)
                    start = pos + i 
                    len_nerword = len(ner_word)
                    pos = start + len_nerword
                    mention = (ner_word, offset + start, offset + start + len_nerword)
                    aHash = ner.get(mention, {})
                    for label in ner[key]:
                      #print (f'found new mention from {target_lang}', mention, label)
                      aHash[label] = aHash.get(label, 0) + ner[key][label]
                    ner[mention] = aHash
                idx = None
                ner_word = ""
                ent2 = ""
            prev_o, prev_t = o, t

        # increase the src_lang ner score if we already matched this ner in src_lang or there was a partial match
        for doc in docs.values():
          bner = doc[f'{src_lang}_2_{target_lang}_backtrans_ner']
          ner = doc[f'{src_lang}_ner']
          for key, aHash in bner.items():
            if key in ner: continue
            ent = key[0]
            ner_match = [key2 for key2 in ner if ent == key2[0]]
            if not ner_match and len(ent) > 3:
              ner_match = [key2 for key2 in ner if (ent in key2[0] or (len(key2[0]) > 3 and key2[0] in ent))]
            all_keys = []
            for key2 in ner_match:
              all_keys.extend(list(ner[key2].keys()))
            all_keys = set(all_keys)
            for label in list(aHash.keys()):
              if label in all_keys or 'MISC' in all_keys:
                    aHash[label] *= 1.1
                    print ('increasing in backtrans ', key, label, aHash[label])
          for key, aHash1 in bner.items():
            ner[key] = aHash2 = ner.get(key, {})
            for key2 in aHash1:
              aHash2[key2] = aHash2.get(key2, 0.0) + aHash1[key2]

        if do_cleanup:
          #do some cleanups. we don't want any ner that are just short numbers, stopwords or single characters.
          for _id, doc in docs.items():
            ner =  doc[f'{src_lang}_ner'] 
            for key in list(doc[f'{src_lang}_ner'].keys()):
              ner_word = key[0]
              try:
                if len(ner_word) < 4 and float(ner_word):
                  print ("deleting ", ner_word)
                  del doc[f'{src_lang}_ner'][key]
                  continue
              except:
                pass
              if ner_word.lower()in stopwords1 or (not self.cjk_detect(ner_word) and len(ner_word) <= 1):
                print ("deleting ", ner_word)
                del doc[f'{src_lang}_ner'][key]

    docs = self.collapse_ner(docs, target_ner_key, target_text_key)
    
    #anonymization is very similar to augmentation, except we operate in the src_lang space, and don't require translation. 
    #we will replace the words directly from {src_lang}_text to {src_lang}_text_anon. we assume all ner process has been completed at this point. 
    #anonymization will create a new {src_lang}_text_anon and {src_lang}_ner_anon field.
    #anohter way to do anonymimzation is to pass the anonymized text through backtrans. TBD?
    context = {}
    if do_anonymization and faker_src_lang is not None and faker_en is not None:
      for doc in docs.values():
          context = doc[f'{src_lang}_anon_context'] = doc.get(f'{src_lang}_anon_context', {})
          if f'{src_lang}_items' not in doc:
            doc[f'{src_lang}_items'] = list(doc.get(f'{src_lang}_ner', {}).keys())
            doc[f'{src_lang}_items'].sort(key=lambda a: a[1], reverse=True)

          ner = doc.get(f'{src_lang}_ner', {})
          idx_items = list(enumerate(doc[f'{src_lang}_items']))
          idx_items.sort(key=lambda a: len(a[1][0]))

          for idx, key in idx_items:
            if key not in ner: continue
            ent = key[0]
            tag = ner[key]
            if ent in context: continue
            #TODO - do proper gender based aug and gender swap
            if 'PERSON' in aug_scope and tag == 'PERSON':
              context[ent] = context.get(ent, faker_en.first_name() + " " + random.choice(bantu_surnames) if " " in ent and src_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh",) else \
                                     random.choice(bantu_surnames) if src_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh",) else \
                                     random.choice(vietnamese_surnames) + " " + random.choice(vietnamese_firstnames) if " " in ent and src_lang =="vi" else \
                                     random.choice(vietnamese_surnames) if  src_lang == "vi" else \
                                     faker_en.first_name() + " " + random.choice(bengali_surnames) if " " in ent and src_lang =="bn" else \
                                     random.choice(bengali_surnames) if src_lang == "bn" else \
                                     random.choice(urdu_firstnames)  + " " + random.choice(urdu_surnames) if " " in ent and src_lang =="ur" else \
                                     random.choice(urdu_surnames) if src_lang == "ur" else \
                                     faker_src_lang.name() if " " in ent else \
                                     faker_src_lang.first_name() )
              
            if 'LOC' in aug_scope and tag == 'LOC':
              context[ent] = context.get(ent, faker_en.country() if  src_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh", "bn", "ur", "vi", "eu") else \
                                     faker_src_lang.state() if src_lang != 'zh' else \
                                     faker_src_lang.province() if  src_lang == 'zh' else 
                                     ent)
            if 'ORG' in aug_scope and tag == 'ORG':
              try:
                context[ent] = context.get(ent, faker_src_lang.company())
              except:
                context[ent] = context.get(ent, faker_en.company())

            if 'ID' in aug_scope and tag == 'ID':
              context[ent] = context.get(ent, str(random.randrange(10000000,999999999)) if src_lang in ("yo", "sw","sn", "st", "ig", "ny", "xh", "bn", "ur", "vi", "eu")  else \
                                     faker_src_lang.ssn())
              
            if 'ADDRESS' in aug_scope and tag == 'ADDRESS':
              context[ent] = context.get(ent, faker_en.address() if src_lang not in ("yo", "sw","sn", "st", "ig", "ny", "xh", "bn", "ur", "vi", "eu") else \
                                     faker_src_lang.address() )
              
            if tag in  ('PESON', 'ORG') and tag in aug_scope :
              src_first, src_last = None, None
              target_first, target_last = None, None
              if src_lang in ("ja", "ko", "zh") and len(ent) > 1:
                src_first, src_last = ent[0], ent[-1]
              elif " " in ent:
                src_first, src_last =  ent.split()[0], ent.split()[-1]
              if src_lang in ("ja", "ko", "zh"):
                target_first, target_last = context[ent][0], context[ent][-1]
              elif " " in context[ent]:
                target_first, target_last = context[ent].split()[0], context[ent].split()[-1]
              if src_first and (src_lang  in ("ja", "ko", "zh") or len(src_first) > 3) and src_first not in context:
                context[src_first] = target_first
              if src_last and (src_lang  in ("ja", "ko", "zh") or len(src_last) > 3) and src_last not in context:
                context[src_last] = target_last
          print (context)
      for chunk in chunks:
          #TODO - finish this code
          context = doc[f'{src_lang}_anon_context'] = doc.get(f'{src_lang}_anon_context', {})
          text = chunk[f'{src_lang}_text']
          _id = chunk['id']
          doc = docs[_id]
          for idx, key in enumerate(doc[f'{src_lang}_items']):
            if do_augment:
              ent = context.get(key[0], key[0])
            else:
              ent = key[0]
            text = text.replace(f" **{idx}** ", f" {idx} {lbracket} {ent} {rbracket}")
          chunk[f'{src_lang}_text_anon'] = text.replace("  ", " ")
          #create {src_lang}_ner_anon
    
    return docs, chunks

  def process_ner(self, 
              src_lang,
              text=None,
              docs=None,
              do_spacy = True,
              do_hf_ner = True,
              do_ontology = True,
              do_backtrans=False,
              do_augment=False,
              do_anonymization=False,
              augment_lang="es",
              do_cleanup=True,
              do_regex = True,
              batch_size = 5, 
              batch_window=70,
              ontology_weight=0.9,
              spacy_weight=1.25,
              hf_ner_weight=1.5,
              regex_weight=2.0,
              backtrans_weight=0.9,
              do_docs_trim=True,
              cutoff=None,
              target_lang='en', 
              domain="",
              aug_scope={'ADDRESS', 'ORG', 'PERSON', 'LOC', 'ID'}, #TODO, public figure, age, norp and disease
              anon_scope={'PERSON', 'ID'}):
      """
      This is the main routine to perform crosslingual NER for a src_lang document with no NER models. 
      It uses a cross lingual NER model that is 'close enough', and also uses backtranslation (target_lang English) to do further NER, and then map back to src_lang.
      It can also create crosslingual augmented data to create additional data for training.
      This routine can also be used to do anonymization of the original src_lang text at the end of the NER pipeline. 
      """
      src_is_cjk = src_lang in ('zh', 'ko', 'ja')
      if src_is_cjk:
        sep = ""
      else:
        sep = " "

      if text is None and docs is None:
        try:
          domain = 'oscar_registry'
          d = load_dataset("TurkuNLP/register_oscar", data_files=f"{src_lang}/{src_lang}_00000*")
          docs = [doc for doc in d['train'] if 'labels' not in doc or doc['labels'] !=[]]
        except:
          try:
            domain = 'mc4_registry'
            d = load_dataset("TurkuNLP/register_mc4", data_files=f"{src_lang}/{src_lang}_00000*")
            docs = [doc for doc in d['train'] if 'labels' not in doc or doc['labels'] !=[]]
          except:
            domain = 'oscar'
            url = _get_oscar_urls(src_lang)[0]
            _download_urls([url])
            docs = [{'text':text}  for text in [try_decode(t) for t in gzip.open(url.split("/")[-1], "rb").readlines()] if text]
      elif docs is None:
        if isinstance(text, str):
          docs = [{'text': text}]
        elif isinstance(text, list):
          if isinstance(text[0], dict):
            docs = text
          else:
            docs = [{'text': t} for t in text]
      #for testing only
      if cutoff is not None and len(docs) > cutoff:
        docs = docs[:cutoff]
      #print (docs)
      len_docs = len(docs)
      for doc in docs:
        doc[f'{src_lang}_text'] = doc['text']
        del doc['text']
      flagged_words1 = set([s for s in flagged_words.get(src_lang, []) if len(s) < 5])
      stopwords1 = set(stopwords.get(src_lang, []))
      docs = [doc for doc in docs if self.check_good_sentence(doc[f'{src_lang}_text'], src_lang, stopwords=stopwords1, flagged_words=flagged_words1)]
      print ('trimmed junk', (len_docs-len(docs))/len_docs)
      len_d = len(docs)
      #flagged_words2 = set([s for s in flagged_words_ac_dc.get(target_lang, []) if len(s) < 5])
      
      counter = {}
      chunks = []
      _id = -1
      for doc in docs:
        _id += 1
        if 'id' not in doc:
          doc['id'] = str(_id)
        doc[f'{src_lang}_text'] = doc[f'{src_lang}_text'].replace("[", "(").replace("]", ")") # we use [] as special chars
        doc['lang'] = src_lang
        doc['domain'] = domain
        doc['chunks'] = [] 
        offset = 0
        if src_is_cjk:
          textarr = doc[f'{src_lang}_text']
        else:
          textarr = doc[f'{src_lang}_text'].split()
        if True:
          text = []
          for t in textarr:
            punc_found = [punc for punc in t if punc in self.punc_char] 
            if punc_found and t[-1] not in self.punc_char and t[0] not in "0123456789" and t[0] == t[0].lower():
              w = t[t.index(punc_found[0])+1]
              if w == w.upper():
                t, t1 = t.split(punc_found[0],1)
                t = t+punc_found[0]+(" " if src_is_cjk else "") 
                text.append(t)
                text.append(t1)
                continue
            text.append(t)
          text[0] = text[0].lstrip()
          text[-1] = text[-1].rstrip()
          doc[f'{src_lang}_text'] = sep.join(text)
          len_text = len(text)
          while len_text > batch_window:
            for j in range(batch_window-1, len_text):
              if (src_is_cjk and text[j] in self.punc_char) or (not src_is_cjk and text[j][-1] in self.punc_char):
                break
            text_str = sep.join(text[:j+1])
            chunks.append({f'{src_lang}_text': text_str, 'id': doc['id'], f'{src_lang}_offset': offset})
            doc['chunks'].append(chunks[-1])
            offset += len(text_str) + (0 if src_is_cjk else 1)
            text = text[j+1:]
            len_text = len(text)
          if text:
            text_str = sep.join(text)
            chunks.append({f'{src_lang}_text': text_str, 'id': doc['id'], f'{src_lang}_offset': offset})
            doc['chunks'].append(chunks[-1])
    
      docs = dict([(doc['id'], doc) for doc in docs])
      if do_docs_trim:
        docs2, chunks2 = self.trim_to_prefer_person(docs, chunks)
        do_docs_trim = len(docs2) == len(docs)
        docs, chunks = docs2, chunks2

      # we do this here because we don't want to trim  ner items that are considered empty.
      # we should probably fix trim_to_prefer_person to not do any trimming if all ner's are empty
      for doc in docs.values():
        doc[f'{src_lang}_ner'] = doc.get(f'{src_lang}_ner', {})
        
      #do ner processing in src_lang with potential anonymization
      docs2, chunks2 = self.process_ner_chunks_with_trans(
                          src_lang, 
                          docs, 
                          chunks, 
                          target_lang=src_lang,
                          do_spacy = do_spacy,
                          do_hf_ner = do_hf_ner,
                          do_ontology = do_ontology,
                          do_backtrans=False,
                          do_augment=False,
                          do_anonymization=do_anonymization if target_lang == src_lang else False,
                          do_regex = do_regex,
                          do_cleanup=do_cleanup,
                          batch_size = batch_size, 
                          ontology_weight=ontology_weight,
                          spacy_weight=spacy_weight,
                          hf_ner_weight=hf_ner_weight,
                          regex_weight=regex_weight,
                          backtrans_weight=backtrans_weight,
                          do_docs_trim=do_docs_trim)
      if do_docs_trim:
        do_docs_trim = len(docs2) == len(docs)
      docs, chunks = docs2, chunks2
      
      if target_lang != src_lang:
        #do ner processing in target language with optional backtrans and anonymization
        docs2, chunks2 = self.process_ner_chunks_with_trans(
                            src_lang, 
                            docs, 
                            chunks, 
                            target_lang = target_lang,
                            do_spacy = do_spacy,
                            do_hf_ner = do_hf_ner,
                            do_ontology = do_ontology,
                            do_backtrans=do_backtrans,
                            do_augment=False,
                            do_anonymization=do_anonymization,
                            do_regex = do_regex,
                            do_cleanup = do_cleanup,
                            batch_size = batch_size, 
                            ontology_weight=ontology_weight,
                            spacy_weight=spacy_weight,
                            hf_ner_weight=hf_ner_weight,
                            regex_weight=regex_weight,
                            backtrans_weight=backtrans_weight,
                            do_docs_trim=do_docs_trim)
        docs, chunks = docs2, chunks2

      assert not do_augment or augment_lang not in (src_lang, target_lang), "augmented langauge should be different than src_lang and target_lang"

      if do_augment:
        #do data augmentation by adding a new text field with fake names, etc. in augment_lang
        docs2, chunks2 = self.process_ner_chunks_with_trans(
                            src_lang, 
                            docs, 
                            chunks, 
                            target_lang = augment_lang,
                            do_spacy = do_spacy,
                            do_hf_ner = do_hf_ner,
                            do_ontology = do_ontology,
                            do_backtrans=False,
                            do_augment=do_augment,
                            do_anonymization=False,
                            do_regex = do_regex,
                            do_cleanup=do_cleanup,
                            batch_size = batch_size, 
                            ontology_weight=ontology_weight,
                            spacy_weight=spacy_weight,
                            hf_ner_weight=hf_ner_weight,
                            regex_weight=regex_weight,
                            backtrans_weight=backtrans_weight,
                            do_docs_trim=do_docs_trim)
        docs, chunks = docs2, chunks2
      return docs, chunks
