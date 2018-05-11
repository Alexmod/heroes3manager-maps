from flask import Flask, render_template, flash, redirect, url_for, request
from flask_pymongo import PyMongo
import json
from bson import json_util
from forms import FormMapGame
from flask_bootstrap import Bootstrap
import datetime
import uuid
import os
from parser import ParserMap
import shutil

app = Flask(__name__)
app.config["SECRET_KEY"] = '632dc6a1-5fef-^&%&*JH4aba-b944-e873ff61b76f'
app.config['MONGO_DBNAME'] = 'heroesmap'
app.config['TEMPLATES_AUTO_RELOAD'] = True
mongo = PyMongo(app)
bootstrap = Bootstrap(app)


@app.after_request
def add_header(response):
    """Запрещаяем всяческое кеширование из-за IE и json и модальных окон"""
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'public, max-age=0'
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get/all/map/_ajax")
def get_all_map_ajax():
    docs_list = list(mongo.db.heroesmap.find({}, {'descr': 0, 'comment': 0,
                                                  'last_game': 0}))
    return json.dumps(docs_list, default=json_util.default)  # indent=4 * ' '


@app.route("/map/get/info/<_id>")
def map_get_info(_id):
    form = FormMapGame()
    info = mongo.db.heroesmap.find_one_or_404({'_id': _id})
    form._id.data = _id
    form.status.data = info.get('status')
    form.comment.data = info.get('comment')
    return render_template("map_get_info.html", info=info, form=form)


@app.route('/set/map/', methods=['POST'])
def set_map():
    form = FormMapGame()
    if form.validate_on_submit():
        _id = form._id.data
        if form.delmap.data:
            query = mongo.db.heroesmap.find_one_or_404({'_id': _id})
            file_name = 'static/Maps/' + query['file_name']
            try:
                os.remove(file_name)
            except OSError:
                pass
            mongo.db.heroesmap.remove({'_id': _id})
            flash('Карта удалена!', 'success')
        else:
            status = form.status.data
            comment = form.comment.data
            last_game = datetime.datetime.now()
            mongo.db.heroesmap.update({'_id': _id},
                                      {'$set': {'status': status,
                                                'comment': comment,
                                                'last_game': last_game}},
                                      upsert=False, multi=False)

            flash('Информация о карте успешно изменена!', 'success')
        return redirect(url_for('index'))


@app.route("/upload/")
def upload():
    return render_template("upload.html")


@app.route("/upload/post/multi/_ajax", methods=["POST"])
def upload_post_multi():
    uploaded_files = request.files.getlist("file[]")
    answer = {}
    for file in uploaded_files:
        fn = '/tmp/' + str(uuid.uuid4())
        file.save(fn)
        res = ParserMap(fn)
        if res.get('_id'):
            _id = res.get('_id')
            if mongo.db.heroesmap.find_one({'_id': _id}):
                answer[file.filename] = 'Такая карта уже есть в каталоге!'
            else:
                new_fn = res['Version'] + '_' + res['name']
                new_fn = "".join([x if x.isalnum() else "_" for x in new_fn])
                new_fn = 'static/Maps/' + new_fn + '.h3m'
                while os.path.exists(new_fn):
                    new_fn = new_fn.split('.')
                    new_fn = "".join(fn[:-1]) + "_." + fn[-1]
                shutil.copy(fn, new_fn)
                if not res.get('encode'):
                    res['encode'] = 'unknown'
                res['file_name'] = os.path.split(new_fn)[1]
                mongo.db.heroesmap.insert_one(res)
                answer[file.filename] = 'Карта успешно записана в каталог!' + \
                    ' С именем:' + res['name']

        else:
            answer[file.filename] = 'Невозможно распознать карту!'

        os.remove(fn)

    return json.dumps(answer, ensure_ascii=False, indent=4 * ' ')


if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
