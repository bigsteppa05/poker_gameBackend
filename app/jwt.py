import jwt
from datetime import datetime,timezone,timedelta
import os
from functools import wraps
from flask import request,jsonify


SECRET_KEY=os.getenv("JWT_SECRET")
ALGORITHM="HS256"

def generate_token(id):

    now=datetime.now(timezone.utc)
    payload={
        "id":id,
        "exp":now+timedelta(hours=24),
        "iat":now
    }

    return jwt.encode(payload,SECRET_KEY,algorithm=ALGORITHM)


def verify_token(token:str):
    try:
        decoded=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        return decoded
    except:
        return None

def require_auth(func):
    @wraps(func)
    async def wrapper(*args,**kwargs):
        auth_header=request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"custom":True,"_message":"Auth headers required"}),401
        
        print("Auth header",auth_header)

        try:
            split_token=auth_header.split(" ")
            print("split token",split_token)
            token_type=split_token[0]
            token_value=split_token[1]
            
            if token_type !="Bearer":
                return jsonify({"custom":True,"_message":"Invalid token type"}),401
            
            decoded=verify_token(token=token_value)

            if not decoded:
                return jsonify({"custom":True,"_message":"Session exipired"}),401
            
            prisma=kwargs.get("prisma")
            _decoded_user=decoded

            if prisma:    
                _decoded_user=await prisma.player.find_unique(
                    where={
                        "id":decoded["id"]
                    }
                )
              

            return  await func(*args,_jwt=_decoded_user,**kwargs)
        

        except Exception as e:
            print("Auth Error",e)
            return jsonify({"custom":True,"_message":"Auth Failed"}),500
        
    return wrapper