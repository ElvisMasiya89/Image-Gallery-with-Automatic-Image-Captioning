from flask import (render_template, request, Blueprint)
from flask_login import current_user
from imagegallery import db
from imagegallery.models import Post
from werkzeug.utils import secure_filename
import base64
import cv2
import numpy as np
from tensorflow.keras.layers import Dense, LSTM, TimeDistributed, Embedding, Activation, RepeatVector, Concatenate,BatchNormalization
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tqdm import tqdm
from tensorflow.keras.models import load_model
from tensorflow.keras.applications import ResNet50

post = Blueprint('post', __name__)
# resnet = ResNet50(include_top=False, weights='imagenet', input_shape=(224,224,3), pooling='avg')
# resnet.save("resnet_model.h5")
resnet = load_model('resnet_model.h5')
print("=" * 50)
print("resnet loaded")

vocab = np.load(r'C:\Users\INTELLICCO\Desktop\ImageGallery\imagegallery\posts\vocab.npy', allow_pickle=True)
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
model.load_weights(r'C:\Users\INTELLICCO\Desktop\ImageGallery\imagegallery\posts\best_weights.h5')
print("=" * 50)
print("resnet loaded")


def prediction():
    global model, vocab, inv_vocab, resnet
    img = cv2.imread(r'C:\Users\INTELLICCO\Desktop\ImageGallery\imagegallery\static\file.jpg')
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


@post.route("/upload", methods=['GET', 'POST'])
def upload():
    pic = request.files['pic']

    if not pic:
        return 'No pic uploaded', 400

    mypic = pic.read()

    pic.stream.seek(0)
    # seek to the beginning of file
    # will point to tempfile itself

    pic.save(r'C:\Users\INTELLICCO\Desktop\ImageGallery\imagegallery\static\file.jpg')
    caption = prediction()

    filename = secure_filename(pic.filename)
    mimetype = pic.mimetype
    img = Post(img=mypic, name=filename, caption=caption, mimetype=mimetype, user=current_user)
    db.session.add(img)
    db.session.commit()

    final = caption
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




  
    