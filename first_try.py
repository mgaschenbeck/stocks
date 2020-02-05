import pandas as pd
import keras
from keras import Model
import numpy as np
from keras.models import Sequential
from keras.layers import Input,Conv1D,Dense,Flatten,Dropout,MaxPooling1D,BatchNormalization,Concatenate
import os
import matplotlib.pyplot as plt
from keras.utils import multi_gpu_model
import tensorflow as tf
from keras.callbacks import TensorBoard
tensorboard = TensorBoard(log_dir="./logs")

output=[]
input=[]
for root,dirs,files in os.walk("Stocks",topdown=False):
    for name in files:
        filename =  os.path.join(root,name)
        print("filename = " , filename)
        openp=[]
        closep=[]
        volume=[]

        df=pd.read_csv(filename)
        for ind,row in df.iterrows():
            openp.append(row["Open"])
            closep.append(row["Close"])
            volume.append(row["Volume"])
         
        openp=np.array(openp)
        closep=np.array(closep)
        volume=np.array(volume)

        open_data = np.array([openp[i:i+64] for i in range(0,df.values.shape[0]-64)])
        close_data = np.array([closep[i:i+64] for i in range(0,df.values.shape[0]-64)])
        volume_data = np.array([volume[i:i+64] for i in range(0,df.values.shape[0]-64)]).astype('float')

        if open_data.shape[0]==0:
            continue        

        #convert open/close to ratio of original:
        for i in range(0,open_data.shape[0]):
            baseline=open_data[i][0]
            if baseline == 0:
                continue
            od=open_data[i]/(baseline)
            cd=close_data[i]/(baseline)
            if od.max()>5 or od.min() < .2 or cd.max()>5 or cd.min() < .2:
                open_data[i]=1.0
                close_data[i]=1.0
            else:
                open_data[i]=od
                close_data[i]=cd
            open_data[i]=open_data[i]-1.0
            close_data[i]=close_data[i]-1.0
        #convert volume to have a mean 0, standard deviation 1
        for i in range(0,open_data.shape[0]):
            volume_data[i]=(volume_data[i]-volume.mean())/(volume.std()+.001)
        
        odi = open_data
        cdi = close_data
        vdi = volume_data
               
        
        current_input= np.stack((odi[:,0:50],cdi[:,0:50],vdi[:,0:50]),1)
        if output==[]:
            output = odi[:,50:64]
            input = current_input
            
        else:
            output = np.vstack((output,odi[:,50:64]))
            input = np.vstack((input,current_input))
            

input = input.transpose([0,2,1])

inputLayer = Input(shape=(50,3))
layers = BatchNormalization()(inputLayer)
#layers = BatchNormalization(input_shape=(50,3))(inputLayer)
layers = Conv1D(128,11,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = Dropout(.3)(layers)
layers = Conv1D(128,3,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = MaxPooling1D(pool_size=2,stride=2,data_format="channels_last")(layers)
layers = BatchNormalization()(inputLayer)
layers = Conv1D(128,3,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = Dropout(.3)(layers)
layers = Conv1D(128,3,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = Dropout(.3)(layers)
layers = Conv1D(128,3,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = MaxPooling1D(pool_size=2,stride=2,data_format="channels_last")(layers)
layers = BatchNormalization()(inputLayer)
layers = Conv1D(128,3,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = Dropout(.3)(layers)
layers = Conv1D(128,3,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = Dropout(.3)(layers)
layers = Conv1D(128,3,data_format="channels_last",use_bias=True,activation='relu')(layers)
layers = Flatten()(layers)
outputLayer = Dense(1,activation='linear')(layers)
model = Model(inputLayer,outputLayer)

simple_layer=inputLayer[:,0,0]
concat_layer = Concatenate()([outputLayer,Flatten()(inputLayer)])
newlayer=Dense(1,activation='linear')(concat_layer)

model = Model(inputLayer,newlayer)
model = multi_gpu_model(model)
model.compile(optimizer='adadelta',loss='mae')
#sgd=keras.optimizers.SGD(learning_rate=0.1, momentum=0.1, nesterov=False)
#model.compile(optimizer=sgd,loss='mse')
#model.fit(input,output[:,0],epochs=10,batch_size=512, validation_split=.2,shuffle=False)
model.fit(input,output[:,10],epochs=5,batch_size=1000, validation_split=.2, shuffle=True)
#model.fit(input,output[:,0],epochs=10,batch_size=1000, validation_split=.2, shuffle=True, callbacks=[tensorboard])
