import json


#read data
with open('final_data_1.json', 'r') as f:
    data = json.load(f)
    
    
final_data = []
    
for value in data:
    
    val = value['word'] + '\t'
    
    if(value['stem_exists']):
        val += value['stem'] + '\t'
    
    if(value['sandhi_split_happens']):
        
        if( '#' in value['sandhi_split'][0] and not value['stem_exists']):
            val += value['word'] + '\t'
            
        elif('-' in value['sandhi_split'][0] and '-' not in value['word']):
            splits = value['sandhi_split'][0].split('-')
            for split in splits:
                val += split + '\t'
        elif(not value['stem_exists']):
            val += value['sandhi_split'][0] + '\t'
    elif(not value['stem_exists']):
        val += value['word'] + '\t'
    if(value['stem_exists']):
        val += value['suffix'] + '\t'
        
    final_data.append(val)
    final_data.append('\n')


#save in file
with open('final_data_test.txt', 'w') as file:
    for val in final_data:
        file.write(val)
        