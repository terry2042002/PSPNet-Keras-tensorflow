from keras.layers import Conv2D, MaxPooling2D, AveragePooling2D
from keras.layers import BatchNormalization, Activation, Input, Dropout, ZeroPadding2D
from keras.layers import merge, concatenate, Lambda, Reshape
from keras.models import Model

import tensorflow as tf



def Interp(x, size=(60,60)):
	print(x.shape)
	new_height = size[0]
	new_width = size[1]
	resized = tf.image.resize_images(x, [new_height, new_width])
	print(resized.shape)
	return resized


def Interp_zoom(x, zoom=8):
	print(x.shape)
	old_height = int(x.shape[1])
	old_width = int(x.shape[2])
	new_height = old_height + (old_height-1) * (zoom - 1)
	new_width = old_width + (old_width-1) * (zoom - 1)
	resized = tf.image.resize_images(x, [new_height, new_width])
	return resized


def residual_conv(prev, level,
				pad=1, lvl=1, sub_lvl=1, modify_stride=False):
	
	lvl = str(lvl)
	sub_lvl = str(sub_lvl)
	names = ["conv"+lvl+"_"+ sub_lvl +"_1x1_reduce" ,
			"conv"+lvl+"_"+ sub_lvl +"_1x1_reduce_bn",
			"conv"+lvl+"_"+ sub_lvl +"_3x3",
			"conv"+lvl+"_"+ sub_lvl +"_3x3_bn",
			"conv"+lvl+"_"+ sub_lvl +"_1x1_increase",
			"conv"+lvl+"_"+ sub_lvl +"_1x1_increase_bn"]
	if modify_stride == False:
		prev = Conv2D(64 * level, (1,1), strides=(1,1), use_bias=False,
					name=names[0])(prev)
	elif modify_stride == True:
		prev = Conv2D(64 * level, (1,1), strides=(2,2), use_bias=False,
					name=names[0])(prev)

	prev = BatchNormalization(momentum=0.95, name=names[1])(prev)
	prev = Activation('relu')(prev)

	prev = ZeroPadding2D(padding=(pad,pad))(prev)
	prev = Conv2D(64 * level, (3,3), 
				strides=(1,1), dilation_rate=pad, use_bias=False,
					name=names[2])(prev)
	

	prev = BatchNormalization(momentum=0.95, name=names[3])(prev)
	prev = Activation('relu')(prev)
	prev = Conv2D(256 * level, (1,1), strides=(1,1), use_bias=False,
					name=names[4])(prev)
	prev = BatchNormalization(momentum=0.95, name=names[5])(prev)
	return prev


def short_convolution_branch(prev, level,
							lvl=1, sub_lvl=1, modify_stride=False):
	lvl = str(lvl)
	sub_lvl = str(sub_lvl)
	names = ["conv"+lvl+"_"+ sub_lvl +"_1x1_proj",
			"conv"+lvl+"_"+ sub_lvl +"_1x1_proj_bn"
			]

	if modify_stride == False:		
		prev = Conv2D(256 * level ,(1,1), strides=(1,1), use_bias=False,
				name=names[0])(prev)
	elif modify_stride == True:
		prev = Conv2D(256 * level, (1,1), strides=(2,2), use_bias=False,
				name=names[0])(prev)

	prev = BatchNormalization(momentum=0.95, name=names[1])(prev)
	return prev


def empty_branch(prev):
	return prev


def residual_short(prev_layer, level, pad=1, lvl=1, sub_lvl=1, modify_stride=False):

	block_1 = residual_conv(prev_layer, level,
						pad=pad, lvl=lvl, sub_lvl=sub_lvl,
						modify_stride=modify_stride)

	block_2 = short_convolution_branch(prev_layer, level,
						lvl=lvl, sub_lvl=sub_lvl,
						modify_stride=modify_stride)

	return merge([block_1, block_2], mode='sum') 


def residual_empty(prev_layer, level, pad=1, lvl=1, sub_lvl=1):
	prev_layer = Activation('relu')(prev_layer)

	block_1 = residual_conv(prev_layer, level, 
						pad=pad, lvl=lvl, sub_lvl=sub_lvl)
	block_2 = empty_branch(prev_layer)
	return merge([block_1, block_2], mode='sum') 


def interp_block(prev_layer, level, str_lvl=1):

	str_lvl = str(str_lvl)

	names = [
		"conv5_3_pool"+str_lvl+"_conv",
		"conv5_3_pool"+str_lvl+"_conv_bn"
		]

	kernel = (10*level, 10*level)
	strides = (10*level, 10*level)
	prev_layer = AveragePooling2D(kernel,strides=strides)(prev_layer)
	prev_layer = Conv2D(512, (1,1), strides=(1,1), use_bias=False, name=names[0])(prev_layer)
	prev_layer = BatchNormalization(momentum=0.95, name=names[1])(prev_layer)
	prev_layer = Activation('relu')(prev_layer)
	prev_layer = Lambda(Interp)(prev_layer)
	return prev_layer


def build_pspnet():
	#Names for the first couple layers of model
	names = ["conv1_1_3x3_s2",
			"conv1_1_3x3_s2_bn",
			"conv1_2_3x3",
			"conv1_2_3x3_bn",
			"conv1_3_3x3",
			"conv1_3_3x3_bn"]

	#---Short branch(only start of network)

	inp = Input((473,473, 3))

	cnv1 = ZeroPadding2D(padding=(1,1))(inp)
	cnv1 = Conv2D(64, (3, 3), strides=(2, 2), use_bias=False, name=names[0])(cnv1) # "conv1_1_3x3_s2"
	
	bn1 = BatchNormalization(momentum=0.95, name=names[1])(cnv1)  # "conv1_1_3x3_s2/bn"
	relu1 = Activation('relu')(bn1)				#"conv1_1_3x3_s2/relu"

	cnv1 = ZeroPadding2D(padding=(1,1))(relu1)
	cnv1 = Conv2D(64, (3, 3), strides=(1, 1), use_bias=False, name=names[2])(cnv1) #"conv1_2_3x3"
	
	bn1 = BatchNormalization(momentum=0.95, name=names[3])(cnv1)  #"conv1_2_3x3/bn"
	relu1 = Activation('relu')(bn1) 				#"conv1_2_3x3/relu"

	cnv1 = ZeroPadding2D(padding=(1,1))(relu1)
	cnv1 = Conv2D(128, (3, 3), strides=(1, 1), use_bias=False, name=names[4])(cnv1) #"conv1_3_3x3"
	
	bn1 = BatchNormalization(momentum=0.95, name=names[5])(cnv1) 		#"conv1_3_3x3/bn"
	relu1 = Activation('relu')(bn1)				#"conv1_3_3x3/relu"

	res = ZeroPadding2D(padding=(1,1))(relu1)
	res = MaxPooling2D(pool_size=(3,3), strides=(2,2))(res)  #"pool1_3x3_s2"
	

	#---Residual layers(body of network)

	"""
	Modify_stride --Used only once in first 3_1 convolutions block.
	changes stride of first convolution from 1 -> 2
	"""

	#2_1- 2_3
	res = residual_short(res, 1, pad=1, lvl=2, sub_lvl=1) 
	for i in range(2):
		res = residual_empty(res, 1, pad=1, lvl=2, sub_lvl=i+2) 

	#3_1 - 3_3
	res = residual_short(res, 2, pad=1, lvl=3, sub_lvl=1, modify_stride=True) 
	for i in range(2): 
		res = residual_empty(res, 2, pad=1, lvl=3, sub_lvl=i+2) 

	#4_1 - 4_6
	res = residual_short(res, 4, pad=2, lvl=4, sub_lvl=1) 
	for i in range(5):
		res = residual_empty(res, 4, pad=2, lvl=4, sub_lvl=i+2) 

	#5_1 - 5_3
	res = residual_short(res, 8, pad=4, lvl=5, sub_lvl=1) 
	for i in range(2):
		res = residual_empty(res, 8, pad=4, lvl=5, sub_lvl=i+2) 

	#---Head of network
	#---PSPNet concat layers with Interpolation

	res = Activation('relu')(res)
	interp_block1 = interp_block(res, 6, str_lvl=1)
	interp_block2 = interp_block(res, 3, str_lvl=2)
	interp_block3 = interp_block(res, 2, str_lvl=3)
	interp_block4 = interp_block(res, 1, str_lvl=6)

	#concat all these layers by 4th axis(3+1).  resulted shape=(1,60,60,4096)
	res = concatenate([res,
					interp_block1,
					interp_block2,
					interp_block3,
					interp_block4], axis=3)

	res = ZeroPadding2D(padding=(1,1))(res)
	res = Conv2D(512, (3, 3), strides=(1, 1), use_bias=False, name="conv5_4")(res)
	
	res = BatchNormalization(momentum=0.95, name="conv5_4_bn")(res)
	res = Activation('relu')(res)
	#res = Dropout(0.1)(res) #used only in training
	res = Conv2D(150, (1, 1), strides=(1, 1), name="conv6")(res)
	res = Lambda(Interp_zoom)(res)


	#Use softmax layer for pixelwise prediction
	curr_width, curr_height, curr_channels = res._shape_as_list()[1:]

	reshape = Reshape((curr_width*curr_height, curr_channels))(res)
	activation = Activation('softmax')(reshape)
	reshape = Reshape((curr_width, curr_height, curr_channels))(activation)

	#End of model
	model = Model(inputs=inp, outputs=reshape)
	return model
