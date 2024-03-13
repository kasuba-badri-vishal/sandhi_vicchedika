import os
import sys
import subprocess as sp
import string
import argparse

import re
import json

#import devtrans as dt
from devconvert import dev2wx, dev2slp, iast2slp, slp2iast, slp2wx, slp2dev, wx2slp, slp2tex

import csv
from aksharamukha import transliterate
import pycdsl
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate as indic_transliterate

vowel_list = ["a", "aa", "i", "ii", "u", "uu", ".r", ".rr", "e", "ai", "o", "au"]

def has_more_than_two_subwords(word):
    count = 0
    for vowel in vowel_list:
        if vowel in word:
            count += 1
            if count >= 1:
                return True
    return False


sentence_modes = {
    "sent" : "t",
    "word" : "f"
}

segmentation_modes = {
    "first" : "s",
    "best" : "l"
}

cgi_file = "./interface2"


def wx2dev(text):
    """
    """
    
    return slp2dev.convert(wx2slp.convert(text))
    

def iast2wx(text):
    """
    """
    
    return slp2wx.convert(iast2slp.convert(text))
    

def wx2iast(text):
    """
    """
    
    return slp2iast.convert(wx2slp.convert(text))
    

def handle_input(input_text, input_encoding):
    """ Modifies input based on the requirement of the Heritage Engine
    """
    
    # Replace special characters with "." since Heritage Segmenter
    # does not accept special characters except "|", "!", "."
    modified_input = re.sub(r'[$@#%&*()\[\]=+:;"}{?/,\\]', ' ', input_text)
    if not (input_encoding == "RN"):
        modified_input = modified_input.replace("'", " ")
    
    normalized_input = re.sub(r'M$', 'm', modified_input)
    normalized_input = re.sub(r'\.m$', '.m', normalized_input)
    
    return normalized_input


def input_transliteration(input_text, input_enc):
    """ Converts input in any given notation to WX  
    """
    
    trans_input = ""
    trans_enc = ""
    
    if input_enc == "DN":
        trans_input = dev2wx.convert(input_text)
        trans_enc = "WX"
    elif input_enc == "RN":
        trans_input = iast2wx(input_text)
        trans_enc = "WX"
    else:
        trans_input = input_text
        trans_enc = input_enc
    
    return (trans_input, trans_enc)


def output_transliteration(output_text, output_enc):
    """ Converts the output which is always in WX to 
        deva or roma
    """
    
    trans_output = ""
    trans_enc = ""
    
    if output_enc == "deva":
        trans_output = wx2dev(output_text)
        trans_enc = "deva"
    elif output_enc == "roma":
        trans_output = wx2iast(output_text)
        trans_enc = "roma"
    else:
        trans_output = output_text
        trans_enc = output_enc
    
    return (trans_output, trans_enc)


def run_sh(cgi_file, input_text, input_encoding, lex="MW", sentence_mode="t",
            us="f", output_encoding="roma", segmentation_mode="l",
            pipeline="t"):
    """ Runs the cgi file with a given word/sentence.  
        
        Returns a JSON
    """
    
    time_out = 30
    
    out_enc = output_encoding if output_encoding in ["roma", "deva"] else "roma"
    
    env_vars = [
        "lex=" + lex,
        "st=" + sentence_mode,
        "us=" + us,
        "font=" + out_enc,
        "t=" + input_encoding,
        "text=" + input_text,#.replace(" ", "+"),
        "mode=" + segmentation_mode,
        "pipeline=" + pipeline
    ]
    
    query_string = "QUERY_STRING=\"" + "&".join(env_vars) + "\""
    command = query_string + " " + cgi_file
    
    p = sp.Popen(command, stdout=sp.PIPE, shell=True)
    try:
        outs, errs = p.communicate(timeout=time_out)
    except sp.TimeoutExpired:
        # os.kill(p.pid)
        result = ""
    else:
        try:
            result = outs.decode('utf-8')
        except:
            result = input_text
    
    return result
    

def handle_result(result):
    """ Returns the results from the JSON
    """
    
    result_json = {}
    status = "Failure"
    
    if result:
        try:
            result_str = result.split("\n")[-1]
            result_json = json.loads(result_str)
            status = "Success"
        except:
            result_json = {}
    else:
        status = "Timeout"
    
    return (status, result_json)


def get_segmentations(input_text, result, out_enc):
    """ Returns the results from the JSON
    """
    
    result_json = {}
    
    if result:
        try:
            result_str = result.split("\n")[-1]
            result_json = json.loads(result_str)
        except:
            result_json = {}
    
    results = result_json.get("segmentation", [])
    segs = results if results else [ input_text ]
    
    segs_2 = [ input_text ] if "error" in segs[0] else segs
    
    segmentations = [output_transliteration(x, out_enc)[0] for x in segs_2]
    
    return segmentations
    

def run_sh_text(cgi_file, input_sent, input_encoding, lex="MW",
                sentence_mode="t", us="f", output_encoding="roma",
                segmentation_mode="l", pipeline="t"):
    """ Handles segmentation for the given input sentence
    """
    
    # SH does not accept special characters in the input sequence.  
    # And it results errors if such characters are found.  
    # Uncomment the following to segment the sentence by ignoring  
    # the special characters.  Currently, the following is commented
    # and the same input is returned as the output.
    
    input_sent = handle_input(input_sent.strip(), input_encoding)
    
    trans_input, trans_enc = input_transliteration(input_sent, input_encoding)
    
    result = run_sh(
        cgi_file, trans_input, trans_enc, lex, sentence_mode, us,
        output_encoding, segmentation_mode, pipeline
    )
    
    segmentations = get_segmentations(input_sent, result, output_encoding)
    
    return segmentations
    



url = "http://10.198.63.39/cgi-bin/SKT/sktdeclin"

def ends_with_suffix(word, suffix_list):
    for suffix in suffix_list:
        if word.endswith(suffix):
            return True
    return False

def get_table_result(table):
    rows = table.find_all('tr')
    if len(rows) > 0:
        first_row = rows[1]
        columns = first_row.find_all('th')
        if len(columns) > 1:
            result = columns[1].get_text(strip=True)
        else:
            print("No content found in the first column of the first row.")
    else:
        print("No rows found in the table.")
        
    return result

def get_prathama_vibhakti(word, gender):
    l_velthuis=indic_transliterate(word,sanscript.DEVANAGARI,sanscript.VELTHUIS)
    
    params = {
        'lex': 'SH',
        'q': l_velthuis,
        't': 'VH',
        'g': gender,
        'font': 'deva'
    }
    response = requests.get(url, params=params)
    try:
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', class_='inflexion')
            if table:
                vibhakti = get_table_result(table)
            else:
                params = { 'lex': 'SH', 'q': l_velthuis, 't': 'VH', 'g': 'Fem', 'font': 'deva'}
                response = requests.get(url, params=params)
                soup = BeautifulSoup(response.text, 'html.parser')
                table = soup.find('table', class_='inflexion')
                gender = 'Fem'
                vibhakti = get_table_result(table)
        else:
            print("Error:", response.status_code)
            vibhakti = None
            
    except:
        vibhakti = None
                 
    if vibhakti and ('Fatal' in vibhakti):
        vibhakti = None
        
    return vibhakti, gender, l_velthuis

# Create an instance of CDSLCorpus321
CDSL = pycdsl.CDSLCorpus()

# Setup dictionaries
dictionaries = ["MW", "AP90", "VCP", "SHS"]
CDSL.setup(dictionaries)


column_index_to_extract = 0  # Adjust as needed, considering 0-based indexing
# Read the CSV file and extract the specified column
with open('/data/BADRI/BharatGPT/sandhi-split/utils/pratyaya.csv', 'r') as csv_file:
    csv_reader = csv.reader(csv_file)
    
    # Use list comprehension to extract the specified column
    suffixes = [row[column_index_to_extract] for row in csv_reader]

    suffixes_iso_temp = [transliterate.process('Devanagari','iso', txt) for txt in suffixes]



suffixes_iso = []
for suffix in suffixes_iso_temp:
    
    if(len(suffix) >= 3):
        for dictionary in dictionaries:
            results = CDSL[dictionary].search(suffix)
            if results:
                suffixes_iso.append(suffix)
                break

suffixes_iso = list(set(suffixes_iso))





final_data = []
suffix_freq = {key: 0 for key in suffixes_iso}
feminine_words = ['aa' 'ii', 'uu', '.rr', 'e', 'ai', 'o', 'au']

tokens = []

def create_word_dictionary(word_list):
    word_dict = {}
    for word in word_list:
        if word in word_dict:
            word_dict[word] += 1
        else:
            word_dict[word] = 1
    return word_dict

def sort_dictionary_by_value(word_dict, reverse=False):
    return dict(sorted(word_dict.items(), key=lambda item: item[1], reverse=reverse))


def remove_punctuation_and_numbers(text):
    pattern = '[' + string.digits + string.ascii_letters + string.punctuation + ']'
    text_without_punctuation = re.sub(pattern, '', text)
    return text_without_punctuation



data_file = '/data/BADRI/BharatGPT/sandhi-split/data/samanantar.txt'




all_words = []
with open(data_file, 'r') as file:
    data = file.read()
    data = remove_punctuation_and_numbers(data)
    sents = data.split("\n")
    for sent in tqdm(sents):
        # print(sent)
        words = sent.split()
        for word in words:
            all_words.append(word)
            
word_dict = create_word_dictionary(all_words)

word_dict = sort_dictionary_by_value(word_dict, reverse=True)

print("Created Unique words")

first_value = True

counted_values = True

    
for token_dev, freq in tqdm(word_dict.items()):
    
    if(counted_values and token_dev =='मुस्लिम'):
        counted_values = False
        continue
        
    if(counted_values):
        continue
    else:
        token_data = {}
        token_data['stem_exists'] = False
        token_data['word'] = token_dev
        token_data['frequency'] = freq
        token = transliterate.process('Devanagari','iso', token_dev)

        token_data['transliterated'] = token

        token_data['gender'] = 'Mas'
        if(ends_with_suffix(token, feminine_words)):
            token_data['gender'] = 'Fem'


        for suffix in suffixes_iso:
            if(token.endswith(suffix) and len(token[:-len(suffix)])>=3):
                for dictionary in dictionaries:
                    results = CDSL[dictionary].search(transliterate.process( 'iso','Devanagari', token[:-len(suffix)]))
                    if results:
                        token_data['stem_exists'] = True
                        token_data['stem'] = transliterate.process( 'iso','Devanagari',token[:-len(suffix)])
                        token_data['suffix'] = transliterate.process( 'iso','Devanagari', suffix)
                        break
            if(token_data['stem_exists']):
                break
            

        if(token_data['stem_exists']):
            token_data['vibhakti'], token_data['gender'], token_data['l_velthuis'] = get_prathama_vibhakti(token_data['stem'], token_data['gender'])
        else:
            token_data['vibhakti'], token_data['gender'], token_data['l_velthuis'] = get_prathama_vibhakti(token_data['word'], token_data['gender'])

        token_data['sandhi_split_happens'] = False
        if(has_more_than_two_subwords(token_data['l_velthuis'])):
            token_data['sandhi_split_happens'] = True
            token_data['sandhi_split'] = run_sh_text(cgi_file, token_dev, "DN", lex="MW", sentence_mode="f", us="f", output_encoding="deva", segmentation_mode="l", pipeline="t")
            if(token_data['vibhakti']):
                token_data['sandhi_split_vibhakti'] = run_sh_text(cgi_file, token_data['vibhakti'], "DN", lex="MW", sentence_mode="f", us="f", output_encoding="deva", segmentation_mode="l", pipeline="t")
        else:
            token_data['sandhi_split'] = None
        final_data.append(token_data)


        with open('final_data_1.json', 'a') as f:
            # Check if it's the first iteration, then dump final_data completely
            if(first_value):
                json.dump(final_data, f, indent=4, ensure_ascii=False)
                first_value = False
            else:
                # For subsequent iterations, append the updated token_data to the existing file
                f.seek(0, 2)  # Move the file pointer to the end
                f.truncate()  # Remove the last closing bracket ']'
                f.write(',\n')  # Add a comma and new line for JSON formatting
                json.dump(token_data, f, indent=4, ensure_ascii=False)
                f.write('\n]')  # Close the list and file
                    

# save json data
import json
with open('final_data.json', 'w') as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)


