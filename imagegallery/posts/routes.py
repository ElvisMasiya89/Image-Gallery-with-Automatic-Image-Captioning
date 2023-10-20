import base64
import os

import cv2
import numpy as np
from flask import render_template, request, Blueprint, redirect, url_for, flash, session
from keras.layers import Dense, LSTM, TimeDistributed, Embedding, Activation, RepeatVector, Concatenate, \
    BatchNormalization
from keras.models import Sequential, Model
from keras.models import load_model
from keras.preprocessing.sequence import pad_sequences
from keras.src.applications import ResNet50
from tqdm import tqdm
from werkzeug.utils import secure_filename

from imagegallery import db
from imagegallery.models import Post, User

post = Blueprint('post', __name__)
resnet = ResNet50(include_top=False, weights='imagenet', input_shape=(224,224,3), pooling='avg')
resnet.save("resnet_model.h5")
resnet = load_model('resnet_model.h5')
print("=" * 50)
print("resnet loaded")

vocab = np.load(os.path.abspath(r'imagegallery\posts\vocab.npy'), allow_pickle=True)
vocab = vocab.item()
inv_vocab = {v: k for k, v in vocab.items()}

# MODEL LOADING
# image model

embedding_size = 128
max_len = 40
vocab_size = len(vocab)

image_model = Sequential()
image_model.add(Dense(embedding_size, input_shape=(2048,), activation='relu',))
image_model.add(BatchNormalization())
image_model.add(RepeatVector(max_len))



# language model
language_model = Sequential()
language_model.add(Embedding(input_dim=vocab_size, output_dim=embedding_size, input_length=max_len))
language_model.add(LSTM(256, return_sequences=True))
language_model.add(TimeDistributed(Dense(embedding_size)))
conca = Concatenate()([image_model.output, language_model.output])
x = LSTM(128, return_sequences=True)(conca)
x = LSTM(512, return_sequences=False)(x)
x = Dense(vocab_size)(x)
out = Activation('softmax')(x)

model = Model(inputs=[image_model.input, language_model.input], outputs=out)
model.compile(loss='categorical_crossentropy', optimizer='RMSprop', metrics=['accuracy'])
model.load_weights(os.path.abspath(r'imagegallery\posts\best_weights.h5'))
print("=" * 50)
print("resnet loaded")


def prediction():
    global model, vocab, inv_vocab, resnet
    img = cv2.imread(os.path.abspath(r'imagegallery\static\file.jpg'))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (224, 224,))
    img = np.reshape(img, (1, 224, 224, 3))

    features = resnet.predict(img).reshape(1, 2048)
    text_in = ['startofseq']
    final = ''
    print("=" * 50)
    print("Getting Captions")

    count = 0

    while tqdm(count < 25):
        count += 1
        encoded = []
        for i in text_in:
            encoded.append(vocab[i])

        padded = pad_sequences([encoded], padding='post', truncating='post', maxlen=max_len)
        sampled_index = np.argmax(model.predict([features, padded]))
        sampled_word = inv_vocab[sampled_index]

        if sampled_word != 'endofseq':
            final = final + ' ' + sampled_word

        text_in.append(sampled_word)

    return final


# Custom function to check user authentication
def is_user_authenticated():
    return 'user_id' in session

# Route for uploading images
@post.route("/upload", methods=['GET', 'POST'])
def upload():
    # Check if the user is logged in
    if not is_user_authenticated():
        flash('Please log in to upload images.', 'info')
        return redirect(url_for('users.login'))

    pic = request.files['pic']

    if not pic:
        return 'No pic uploaded', 400

    mypic = pic.read()

    pic.stream.seek(0)
    pic.save(os.path.abspath(r'imagegallery\static\file.jpg'))
    caption = prediction()

    filename = secure_filename(pic.filename)
    mimetype = pic.mimetype

    # Get the current user based on their session ID
    user_id = session['user_id']
    user = User.query.get(user_id)

    img = Post(img=mypic, name=filename, caption=caption, mimetype=mimetype, user=user)
    db.session.add(img)
    db.session.commit()

    final = caption
    flash('Image uploaded successfully!', 'success')
    return render_template("account.html", final=final)

@post.route('/search', methods=["GET"])
def search():
    q = request.args.get('q')
    if q:
        img = Post.query.filter(Post.caption.contains(q)).all()
        print(img)
        if len(img) > 0:
            new_img = []
            count = len(img)
            for i in range(0, count):
                temp = (base64.b64encode(img[i].img).decode('ascii'))
                new_img.append(temp)
            return render_template("search_results.html", img=new_img, count=count)

        else:
            return render_template("search_results.html")

    else:
        return render_template("search_results.html")
    