from flask import Flask,render_template,redirect,request,flash,make_response
import os
import hashlib
import datetime
from cloudant.client import Cloudant
from cloudant import query,result,document


app = Flask(__name__)
app.secret_key = 'lionel'

PORT = os.getenv('PORT', '5000');

USERNAME="<USERNAME>";
PASSWORD="<PASSWORD>";
URL="<CLOUDANT_DB_URL>";
client = Cloudant(USERNAME, PASSWORD, url="<URL>");

UPLOAD_FOLDER=os.path.dirname(__file__)+"/tmp/";
app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER;

@app.route('/')
def home():
    filelist=retrieve_files();
    return render_template("upload.html",files=filelist);


@app.route('/upload',methods=['POST'])
def upload():
    f = request.files['fileToUpload'];
    file_name = f.filename;
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], file_name));
    contents = '';
    hash_content = hashlib.md5();
    with open(UPLOAD_FOLDER + file_name, 'rb') as content_file:
        contents = content_file.read();
        hash_content.update(contents);
    print(hash_content.hexdigest());

    client.connect();

    db = client['lionelfilestorage'];
    file_version_query=query.Query(db,selector={'file_name':file_name});
    version_no=-1;
    is_file_exists=False;
    with query.Query.custom_result(file_version_query) as query_result:
        for doc in query_result:
            version_no = doc["version_no"];
            if doc['file_hashvalue'] == hash_content.hexdigest():
                is_file_exists=True;
                break;
    msg =''
    if is_file_exists==True:
        msg='File already exists,cant upload the same file.'
    else :
        version_no=1 if version_no==-1 else version_no+1;
        file_doc = {
            '_id':file_name+str(version_no),
            'file_name': file_name,
            'file_content': contents,
            'version_no': version_no,
            'file_hashvalue':hash_content.hexdigest(),
            'last_modified':str(datetime.datetime.now()),
            'type':'filedoc'
        }
        db.create_document(file_doc);
        msg='File uploaded sucessfully';
    client.disconnect();
    os.remove(UPLOAD_FOLDER + file_name);
    flash(msg);
    return redirect("/");

@app.route('/delete',methods=['GET','POST'])
def delete():
    if request.method=='POST':
        msg='';
        try :
            file_name = request.form['file_name'];
            version_no = request.form['version_no'];
            client.connect();
            db = client['lionelfilestorage'];
            my_doc = db[file_name + version_no];
            my_doc.delete();
            msg='File deleted successfully';
        except KeyError:
            msg='File not found for deletion';
        except Exception:
            msg='Some issue occured';
        finally:
            client.disconnect();
        flash(msg);
    filelist=retrieve_files();
    return render_template("delete.html",files=filelist);

@app.route('/download',methods=['GET','POST'])
def download():
    if request.method=='POST':
        try:
            file_name = request.form['file_name'];
            version_no = request.form['version_no'];
            client.connect();
            db = client['lionelfilestorage'];
            my_doc = db[file_name + version_no];
            response = make_response(my_doc['file_content']);
            response.headers["Content-Disposition"] = "attachment; filename=" +file_name;
            msg = 'File downloaded successfully';
            flash(msg);
            return response;
        except KeyError:
            msg='File not found for download';
        except Exception:
            msg='Some issue occured';
        finally:
            client.disconnect();
        flash(msg);
    filelist = retrieve_files();
    return render_template("download.html",files=filelist);

def retrieve_files():
    list=[];
    client.connect();
    db = client['lionelfilestorage'];
    file_version_query = query.Query(db, selector={'type':'filedoc'});
    with query.Query.custom_result(file_version_query) as query_result:
        for doc in query_result:
            list.append(doc);
    client.disconnect();
    return list;

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(PORT))
    #app.run()
