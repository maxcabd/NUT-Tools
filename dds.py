import io
from array import array
from PIL import Image
from utils.PyBinaryReader.binary_reader.binary_reader import BinaryReader, Endian
from utils.xfbin_lib.xfbin.structure import nut

from utils.xfbin_lib.xfbin.structure.nucc import NuccChunkTexture
from utils.xfbin_lib.xfbin.structure.nut import NutTexture
from brDDS import BrDDS, BrDDS_Header, BrDDS_PixelFormat, BrDDS_DX10_Header

class DDS:
	def init_data(self, dds: BrDDS):
		self.magic = 'DDS '
		self.header = BrDDS_Header()
		self.header.init_data(dds.header)
		self.mipmaps = dds.mipmaps
		self.texture_data = dds.texture_data

class DDS_Header:
	def init_data(self, dds1: BrDDS_Header):
		self.size = dds1.size
		self.flags = dds1.flags
		self.height = dds1.height
		self.width = dds1.width
		self.pitchOrLinearSize = dds1.pitchOrLinearSize
		self.depth = dds1.depth
		self.mipmap_count = dds1.mipmap_count
		self.reserved = dds1.reserved
		self.pixel_format = dds1.pixel_format
		self.caps1 = dds1.caps1
		self.caps2 = dds1.caps2
		self.caps3 = dds1.caps3
		self.caps4 = dds1.caps4
		self.reserved2 = dds1.reserved2
		
class DDS_PixelFormat:
	def init_data(self, dds2: BrDDS_PixelFormat):
		self.size = dds2.size
		self.flags = dds2.flags
		self.fourCC = dds2.four_cc
		self.rgbBitCount = dds2.rgbBitCount
		self.bitmaks = dds2.bitmasks

class DDS_DX10_Header:
	def init_data(self, dds3: BrDDS_DX10_Header):
		self.dxgi_format = dds3.dxgi_format
		self.resource_dimension = dds3.resource_dimension
		self.misc_flag = dds3.misc_flag
		self.array_size = dds3.array_size
		self.misc_flags2 = dds3.misc_flags2


nut_pf_fourcc  = {
	'DXT1' : 0,
	'DXT3' : 1,
	'DXT5' : 2,

}

nut_pf_bitmasks = {
    (0xf800, 0x7e0, 0x1f, 0): 8,
    (0x7c00, 0x3e0, 0x1f, 0x8000): 6,
    (0x0f00, 0x00f0, 0x000f, 0xf000): 7,
    (0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000): 17,
}

nut_bpp = {
    8: 2,
    6: 2,
    7: 2,
    17: 4,
}

def DDS_to_NutTexture(dds):
	dds: BrDDS
	nut = NutTexture()

	nut.width = dds.header.width
	nut.height = dds.header.height

	if dds.header.pixel_format.fourCC != '':
		nut.pixel_format = nut_pf_fourcc[dds.header.pixel_format.fourCC]
		nut.mipmaps = dds.mipmaps
		nut.texture_data = dds.texture_data
	elif dds.header.pixel_format.bitmasks:
		nut.pixel_format = nut_pf_bitmasks[dds.header.pixel_format.bitmasks]
		nut.mipmaps = list()
		nut.texture_data = b''

		if nut.pixel_format == 17:
			for mip in dds.mipmaps:
				mip = array('l', mip)
				mip.byteswap()
				nut.mipmaps.append(mip.tobytes())
				nut.texture_data += mip.tobytes()

		else:
			for mip in dds.mipmaps:
				mip = array('u', mip)
				mip.byteswap()
				nut.mipmaps.append(mip.tobytes())
				nut.texture_data += mip.tobytes()

	nut.mipmap_count = dds.header.mipMapCount

	nut.is_cube_map = False
	nut.cubemap_format = 0

	nut.data_size = len(dds.texture_data)

	if dds.header.mipMapCount > 1:
		nut.header_size =  80 + (dds.header.mipMapCount * 4)
	else:
		nut.header_size = 80

	nut.total_size = nut.data_size + nut.header_size

	return nut

def NutTexture_to_DDS(nuttex: NutTexture):
	dds = DDS()
	dds.magic = 'DDS '
	header = dds.header = DDS_Header()
	header.pixel_format = DDS_PixelFormat()
	header.size = 124
	header.flags = 0x1 | 0x2 | 0x4 | 0x1000 #DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PIXELFORMAT

	header.width = nuttex.width
	header.height = nuttex.height
	header.mipMapCount = nuttex.mipmap_count

	#check if nuttex.pixel_format is in nut_pf_fourcc
	if nuttex.pixel_format in nut_pf_fourcc.values():
		print('fourcc')

		header.pixel_format.fourCC = list(nut_pf_fourcc.keys())[list(nut_pf_fourcc.values()).index(nuttex.pixel_format)]
		header.flags |= 0x80000 #LINEAR_SIZE
		header.pixel_format.flags = 0x4 #DDPF_FOURCC
		
		if header.pixel_format.fourCC == 'DXT1':
			header.pitchOrLinearSize = nuttex.width * nuttex.height // 2
		else:
			header.pitchOrLinearSize = nuttex.width * nuttex.height
		
		header.pixel_format.rgbBitCount = 0
		header.pixel_format.bitmasks = (0, 0, 0, 0)

		dds.mipmaps = nuttex.mipmaps
		dds.texture_data = nuttex.texture_data
		
		
	elif nuttex.pixel_format in nut_pf_bitmasks.values():
		header.flags |= 0x8 #DDSD_PITCH
		header.pitchOrLinearSize = nuttex.width * nut_bpp[nuttex.pixel_format]
		header.pixel_format.fourCC = None
		header.pixel_format.rgbBitCount = nut_bpp[nuttex.pixel_format] * 8
		header.pixel_format.bitmasks = list(nut_pf_bitmasks.keys())[list(nut_pf_bitmasks.values()).index(nuttex.pixel_format)]
		if nuttex.pixel_format in (6, 7, 17):
			header.pixel_format.flags = 0x40 | 0x01 #DDPF_RGB | DDPF_ALPHAPIXELS
		else:
			header.pixel_format.flags = 0x40 #DDPF_RGB
		
		if nuttex.pixel_format in (6, 7, 8):
			dds.mipmaps = nuttex.mipmaps
			texture_data = array('u', nuttex.texture_data)
			texture_data.byteswap()
			dds.texture_data = texture_data.tobytes()
		elif nuttex.pixel_format == 17:
			dds.mipmaps = nuttex.mipmaps
			texture_data = array('l', nuttex.texture_data)
			texture_data.byteswap()
			dds.texture_data = texture_data.tobytes()

	header.pixel_format.size = 32
	if header.mipMapCount > 1:
		header.flags |= 0x20000 #DDSD_MIPMAPCOUNT
		header.caps1 = 0x8 | 0x1000 | 0x400000 
	else:
		header.caps1 = 0x8 
	header.depth = 1
	header.reserved = [0] * 11
	header.caps2 = 0
	header.caps3 = 0
	header.caps4 = 0
	header.reserved2 = 0
	
	br = BinaryReader(endianness= Endian.LITTLE)
	br.write_struct(BrDDS(), dds)
	return br.buffer()


def write_dds(texture, path):
	for i, tex in enumerate(texture.nut.textures):
		save = f'{path}/{texture.name}_{i}.dds'
		print(f'Writing {save}')
		with open(save, 'wb') as f:
			f.write(NutTexture_to_DDS(tex))
		f.close()

def write_png(texture: NuccChunkTexture, path):
	for i, tex in enumerate(texture.nut.textures):
		save = f'{path}/{texture.name}_{i}.png'
		print(f'Writing {save}')
		if tex.pixel_format == 0 or tex.pixel_format == 1 or tex.pixel_format == 2:
			dxt1 = NutTexture_to_DDS(tex)
			img = Image.open(io.BytesIO(dxt1)).save(save, 'PNG')
		elif tex.pixel_format == 6:
			texture_5551(tex.texture_data, tex.width, tex.height).save(save, 'PNG')
		elif tex.pixel_format == 7:
			texture_4444(tex.texture_data, tex.width, tex.height).save(save, 'PNG')
		elif tex.pixel_format == 8:
			texture_565(tex.texture_data, tex.width, tex.height).save(save, 'PNG')
		elif tex.pixel_format == 14 or tex.pixel_format == 17:
			texture_8888(tex.texture_data, tex.width, tex.height).save(save, 'PNG')

def texture_565(texture_data, width, height):
	texture_data = array('u', texture_data)
	texture_data.byteswap()

	return Image.frombytes('RGB', (width,height), texture_data.tobytes(), 'raw', 'BGR;16')

def texture_5551(texture_data, width, height):
	texture_data = array('u', texture_data)
	texture_data.byteswap()

	return Image.frombytes('RGBA', (width,height), texture_data.tobytes(), 'raw', 'BGRA;15')

def texture_4444(texture_data, width, height):
	texture_data = array('u', texture_data)
	texture_data.byteswap()

	image = Image.frombytes('RGBA', (width,height), texture_data.tobytes(), 'raw', 'RGBA;4B')
	r, g, b, a = image.split()
	return Image.merge('RGBA', (b, g, r, a))

def texture_8888(texture_data, width, height):
	image = Image.frombytes('RGBA', (width,height), texture_data, 'raw')	
	r, g, b, a = image.split()
	return Image.merge('RGBA', (g, b, a, r))
