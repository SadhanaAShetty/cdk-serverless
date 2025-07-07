import json
import boto3
import logging
import urllib.parse
import uuid
import os
from dateutil import parser
import re


logger = logging.getLogger()
logger.setLevel(logging.INFO)


s3 = boto3.client('s3')
textract = boto3.client('textract')
comprehend = boto3.client('comprehend')


source_bucket = os.environ.get("UPLOAD_BUCKET")
target_bucket = os.environ.get("PARSED_BUCKET")

def lambda_handler(event, context):
    try:
        logger.info(f"Triggered by event: {json.dumps(event)}")

       
        triggered_bucket = event['Records'][0]['s3']['bucket']['name']
        object_key = event['Records'][0]['s3']['object']['key']
        logger.info(f"S3 Trigger - Bucket: {triggered_bucket}, Key: {object_key}")

        
        if triggered_bucket == target_bucket:
            logger.info("File is already in the parsed bucket. Skipping processing.")
            return

        if not object_key.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.warning(f"Unsupported file format: {object_key}")
            return {
                'statusCode': 400,
                'body': json.dumps('Unsupported file type')
            }
        
        safe_key = urllib.parse.unquote_plus(object_key)

       
        textract_result = textract.analyze_document(
            Document={'S3Object': {'Bucket': triggered_bucket, 'Name': safe_key}},
            FeatureTypes=['TABLES', 'FORMS']
        )

        lines = extract_text_lines(textract_result)
        full_text = "\n".join(lines)

     
        comprehend_result = comprehend.detect_entities(
            Text=full_text,
            LanguageCode='en'
        )

       
        parsed_receipt = parse_receipt_data(lines, comprehend_result)
        logger.info(f"Parsed Receipt: {parsed_receipt}")

        
        write_result_to_s3(parsed_receipt, object_key)

        return {
            'statusCode': 200,
            'body': json.dumps('Receipt processed and saved successfully!')
        }

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('An error occurred during processing.')
        }

def extract_text_lines(textract_response):
    return [
        block['Text']
        for block in textract_response['Blocks']
        if block['BlockType'] == 'LINE'
    ]

def parse_receipt_data(text_lines, comprehend_output):
    receipt = {'ReceiptId': str(uuid.uuid4())}
    vendor = None
    total = None
    receipt_date = None

    for entity in comprehend_output['Entities']:
        if entity['Type'] == 'ORGANIZATION' and not vendor:
            vendor = entity['Text']
        elif entity['Type'] == 'DATE' and not receipt_date:
            receipt_date = entity['Text']

   
    for line in text_lines:
        if 'total' in line.lower():
            parts = line.split()
            for part in parts:
                if part.replace('.', '', 1).isdigit():
                    total = part
                    break
            if total:
                break

    
    final_date = find_date_in_text(text_lines)

    receipt['Vendor'] = vendor or 'Unknown'
    receipt['Total'] = total or 'Unknown'
    receipt['Date'] = final_date or 'Unknown'

    return receipt

def find_date_in_text(lines):
    date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    for line in lines:
        match = re.search(date_pattern, line)
        if match:
            try:
                dt = parser.parse(match.group(), fuzzy=False)
                if 1900 < dt.year < 2100:
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                continue
    return None

def write_result_to_s3(data, original_key):
    filename = original_key.split('/')[-1]
    json_key = 'parsed-results/' + filename.replace('.jpg', '.json').replace('.png', '.json')

    s3.put_object(
        Bucket=target_bucket,
        Key=json_key,
        Body=json.dumps(data),
        ContentType='application/json'
    )
