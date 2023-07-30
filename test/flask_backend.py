import os
import uuid
import requests
from flask import Flask, request, jsonify, send_from_directory, url_for
from config import APP_ID, APP_SECRET, MONGODB_URI

app = Flask(__name__)

# Connect to MongoDB
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Create a new client and connect to the server
client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
db = client['mydatabase']

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# create a directory for storing uploaded photos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# create a directory for storing user avatars
AVATAR_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'avatars')
if not os.path.exists(AVATAR_FOLDER):
    os.makedirs(AVATAR_FOLDER)

# Define the collections
uploads_collection = db['uploads']
users_collection = db['users']

# Example endpoint to handle the login request
@app.route('/api/login', methods=['POST'])
def login():
    code = request.json['code']

    # Make a request to the WeChat code2session API
    response = requests.get(
        'https://api.weixin.qq.com/sns/jscode2session',
        params={
            'appid': APP_ID,
            'secret': APP_SECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
    )

    if response.status_code == 200:
        print(response.json())
        session = response.json().get('session_key')
        user_id = response.json().get('openid')

        # Check if the user_id exists in the usercollection
        user = users_collection.find_one({'user_id': user_id})
        if user:
            # Retrieve the user information
            nickname = user['nickname']
            avatar_url = user['avatar_url']
            contact_info = user['contact_info']
            
            # Return the user information to the frontend
            user_info = jsonify({
                'session': session,
                'user_id': user_id,
                'nickname': nickname,
                'avatar_url': avatar_url,
                'contact_info': contact_info
            })
            return user_info

        # Store the session in your database or return it to the client
        return jsonify({
            'session': session,
            'user_id': user_id
        })

    # Handle code2session API error
    return jsonify({'error': 'Code2session API error'})

# Endpoint to receive user info
@app.route('/api/user', methods=['POST'])
def add_user():
    # Get the user info from the request
    user_info = request.headers

    # Extract the fields from the user info
    nickname = user_info.get('nickname')
    contact_info = user_info.get('contact_info')
    user_id = user_info.get('user_id')

    # save the file
    file = request.files['file']
    print (request.files)
    filename = file.filename
    file.save(os.path.join(AVATAR_FOLDER, filename))

    # Create a new user document
    update_user = {
        "$set": {
            'nickname': nickname,
            'avatar_url': url_for('download_avatar', filename=filename, _external=True),
            'contact_info': contact_info,
            'user_id': user_id
        }
    }

    # Insert the user document into the MongoDB collection
    users_collection.update_one(filter={'user_id': user_id}, update=update_user, upsert=True)

    # Return the inserted user ID
    return jsonify({
        'user_id': user_id
    })

# endpoint to get unique post_id
@app.route('/api/newpost', methods=['POST'])
def new_post():
    post_id = str(uuid.uuid4())
    while uploads_collection.find_one({'post_id': post_id}):
        post_id = str(uuid.uuid4())
    return jsonify({
        'post_id': post_id
    })

# endpoint to upload a file
@app.route('/api/upload', methods=['POST'])
def upload():
    # get the user ID from the request headers
    user_id = request.headers.get('user_id')

    # check if the post ID already exists
    post_id = str(uuid.uuid4())
    while post_id in db:
        post_id = str(uuid.uuid4())

    # save the file
    file = request.files['file']
    filename = post_id + '-' + file.filename
    text = request.headers.get('text')
    file.save(os.path.join(UPLOAD_FOLDER, filename))

    # Create the file document
    file_doc = {
        'post_id': post_id,
        'user_id': user_id,
        'filename': filename,
        'filepath': url_for('download', filename=filename, _external=True),
        'text': text,
    }

    # Insert the file document into the uploads collection
    uploads_collection.insert_one(file_doc)

    return jsonify({
        'post_id': post_id
    })

# endpoint to get the list of uploaded files for all users
@app.route('/api/list', methods=['GET'])
def list_files():
    # Find all files in the uploads collection
    files = uploads_collection.find()

    # Create a set to store unique post IDs
    post_ids = set()

    # Iterate over the files and add post IDs to the set
    for file in files:
        post_ids.add(file['post_id'])

    # Convert the set to a list
    post_ids = list(post_ids)

    return jsonify({
        'post_ids': post_ids
    })

# endpoint to get the list of uploaded files for a given user ID
@app.route('/api/list/<user_id>', methods=['GET'])
def list_files_by_user(user_id):
    # Get the user ID from the request headers
    user_id = request.headers.get('user_id')

    # Find all files for the given user ID
    files = uploads_collection.find({'user_id': user_id})

    # Create the list of post IDs and file URLs
    post_ids = []
    file_urls = []
    for file in files:
        post_ids.append(file['post_id'])
        file_urls.append(file['filepath'])

    return jsonify({
        'post_ids': post_ids,
        'file_urls': file_urls
    })

# endpoint to get the details of a specific uploaded file
@app.route('/api/details/<post_id>', methods=['GET'])
def file_details(post_id):
    # Find the file with the given post ID
    file = uploads_collection.find_one({'post_id': post_id})

    if not file:
        return jsonify({
            'error': 'Post not found'
        }), 404

    return jsonify(file)

# endpoint to download the specific file
@app.route('/api/download/<path:filename>', methods=['GET'])
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# endpoint to download the specific avatar
@app.route('/api/avatar/<path:filename>', methods=['GET'])
def download_avatar(filename):
    return send_from_directory(AVATAR_FOLDER, filename)


if __name__ == '__main__':
    app.run(debug=True)