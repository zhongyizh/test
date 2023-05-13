from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, url_for
import os
import uuid
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response


@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)


# create a directory for storing uploaded photos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# define the database of uploaded files
db = {}

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

    # add the file to the database
    db[post_id] = {
        'user_id': user_id,
        'filename': filename,
        'filepath': url_for('download', filename=filename, _external=True),
        'text': text,
    }

    return jsonify({
        'post_id': post_id
    })

# endpoint to get the list of uploaded files for all users
@app.route('/api/list', methods=['GET'])
def list_files():
    # get the list of post IDs for all users
    post_ids = [post_id for post_id in db]

    # return the list of post IDs
    return jsonify({
        'post_ids': post_ids
    })

# endpoint to get the list of uploaded files for a given user ID
@app.route('/api/list/<user_id>', methods=['GET'])
def list_files_by_user(user_id):
    # get the list of post IDs for the given user ID
    post_ids = [post_id for post_id in db if db[post_id]['user_id'] == user_id]

    # return the list of post IDs
    return jsonify({
        'post_ids': post_ids
    })

# endpoint to get the details of a specific uploaded file
@app.route('/api/details/<post_id>', methods=['GET'])
def file_details(post_id):
    # check if the post ID exists
    if post_id not in db:
        return jsonify({
            'error': 'Post not found'
        }), 404

    # get the file details
    file_details = db[post_id]
    print(file_details)

    return jsonify(file_details)

# endpoint to download the specific file
@app.route('/api/uploads/<path:filename>', methods=['GET'])
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

