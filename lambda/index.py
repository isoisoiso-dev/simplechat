# lambda/index.py
import json
import os
import re
import requests  # FastAPIにリクエストを送るために追加
# import boto3  # ★不要になったためコメントアウト
# from botocore.exceptions import ClientError  # ★不要になったためコメントアウト

# FastAPIのエンドポイントURL (環境変数から取得。なければデフォルトを使用)
FASTAPI_ENDPOINT = os.environ.get("FASTAPI_ENDPOINT", "https://e40b-35-194-164-86.ngrok-free.app/predict")

# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"

# グローバル変数としてクライアントを初期化（初期値）
# bedrock_client = None  # ★不要になったためコメントアウト

# MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")  # ★不要になったためコメントアウト

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # FastAPIに送るためのペイロードを準備
        request_payload = {
            "messages": messages
        }
        
        print("Calling FastAPI endpoint:", FASTAPI_ENDPOINT)
        print("Payload:", json.dumps(request_payload))

        # FastAPIエンドポイントにPOSTリクエストを送信
        response = requests.post(
            FASTAPI_ENDPOINT,
            headers={"Content-Type": "application/json"},
            data=json.dumps(request_payload)
        )
        
        # レスポンスチェック
        if response.status_code != 200:
            raise Exception(f"FastAPI server returned status {response.status_code}: {response.text}")

        response_body = response.json()
        print("FastAPI response:", json.dumps(response_body, default=str))
        
        # アシスタントの応答を取得
        assistant_response = response_body.get("response")
        if not assistant_response:
            raise Exception("No response content from FastAPI server")
        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
