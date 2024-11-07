import jwt
import datetime as dt
 
def decode_jwt_token(token):

    # Decodes the jwt token into a payload
    secret_key=""
    algorithm="HS256"
    payload=None
    try:
        datenow=dt.datetime.utcnow()
        payload = jwt.decode(jwt=token, 
                            key=secret_key,
                            algorithms=[algorithm]
                            )
        id_user=payload['id_user']
        print (id_user)
        print(str(datenow.isoformat()))
    except Exception as ex:
        print(str(ex))

    return payload


payload=decode_jwt_token("")
print(payload)
