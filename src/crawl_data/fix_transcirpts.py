import json
import os

def process_youtube_transcripts(input_dir="data/transcripts", output_dir="data/processed_transcripts"):
    os.makedirs(output_dir, exist_ok=True)
    
    for filename in os.listdir(input_dir):
        if not filename.endswith(".json"):
            continue
            
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        merged_data = []
        i = 0
        
        while i < len(data):
            if i + 1 < len(data):
                item1 = data[i]
                item2 = data[i+1]
                
                # Giữ nguyên start và duration của item đầu tiên trong cặp
                new_start = item1['start']
                new_duration = item1['duration'] 
                
                new_text = f"{item1['text'].strip()} {item2['text'].strip()}"
                
                merged_data.append({
                    "start": new_start,
                    "duration": new_duration,
                    "text": new_text
                })
                i += 2 
            else:
                merged_data.append(data[i])
                i += 1
                
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=4)
            
    print(f"Đã gộp xong! Kết quả lưu tại: {output_dir}")

process_youtube_transcripts()