import boto3
import json

cognito = boto3.client("cognito-idp", region_name="ap-southeast-1")

def get_user_pool_id(pool_name):
    try:
        response = cognito.list_user_pools(MaxResults=50)
        for pool in response.get("UserPools", []):
            if pool["Name"] == pool_name:
                return pool["Id"]
    except Exception as e:
        print(f"Error listing user pools: {e}")
    return None

def create_user_pool(pool_name):
    print(f"Creating User Pool {pool_name}...")
    try:
        response = cognito.create_user_pool(
            PoolName=pool_name,
            Policies={
                "PasswordPolicy": {
                    "MinimumLength": 8,
                    "RequireUppercase": True,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": True
                }
            },
            AutoVerifiedAttributes=["email"]
        )
        pool_id = response["UserPool"]["Id"]
        print(f"User Pool created successfully. ID: {pool_id}")
        return pool_id
    except Exception as e:
        print(f"Error creating user pool: {e}")
        return None

def get_client_id(pool_id, client_name):
    try:
        response = cognito.list_user_pool_clients(UserPoolId=pool_id, MaxResults=50)
        for client in response.get("UserPoolClients", []):
            if client["ClientName"] == client_name:
                return client["ClientId"]
    except Exception as e:
        print(f"Error listing clients: {e}")
    return None

def create_user_pool_client(pool_id, client_name):
    print(f"Creating User Pool Client {client_name}...")
    try:
        response = cognito.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=client_name,
            GenerateSecret=False, # standard for SPAs
            ExplicitAuthFlows=[
                "ALLOW_USER_PASSWORD_AUTH",
                "ALLOW_REFRESH_TOKEN_AUTH"
            ]
        )
        client_id = response["UserPoolClient"]["ClientId"]
        print(f"User Pool Client created. ID: {client_id}")
        return client_id
    except Exception as e:
        print(f"Error creating user pool client: {e}")
        return None

def create_test_user(pool_id, username, email, password):
    print(f"Checking if user {username} exists...")
    try:
        cognito.admin_get_user(UserPoolId=pool_id, Username=username)
        print(f"User {username} already exists.")
        return
    except cognito.exceptions.UserNotFoundException:
        pass
    except Exception as e:
        print(f"Error checking user: {e}")
        return

    print(f"Creating test user {username}...")
    try:
        cognito.admin_create_user(
            UserPoolId=pool_id,
            Username=username,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"}
            ],
            TemporaryPassword=password,
            MessageAction="SUPPRESS"
        )
        print("User created. Confirming user...")
        # Set permanent password so user does not need to change it on first login
        cognito.admin_set_user_password(
            UserPoolId=pool_id,
            Username=username,
            Password=password,
            Permanent=True
        )
        print(f"User {username} created and confirmed successfully!")
    except Exception as e:
        print(f"Error creating user: {e}")

if __name__ == "__main__":
    pool_name = "WaterQualityUserPool"
    client_name = "WaterQualityWebClient"
    
    pool_id = get_user_pool_id(pool_name)
    if not pool_id:
        pool_id = create_user_pool(pool_name)
    else:
        print(f"User Pool already exists: {pool_id}")

    if pool_id:
        client_id = get_client_id(pool_id, client_name)
        if not client_id:
            client_id = create_user_pool_client(pool_id, client_name)
        else:
            print(f"User Pool Client already exists: {client_id}")
            
        if client_id:
            # Create standard credentials
            create_test_user(pool_id, "admin", "admin@waterquality.com", "Password123!")
            
            # Print environment details
            print("\n" + "="*50)
            print("Cognito Configuration Details:")
            print(f"USER_POOL_ID={pool_id}")
            print(f"APP_CLIENT_ID={client_id}")
            print("="*50)
