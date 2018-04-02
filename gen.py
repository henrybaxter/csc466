# gen.py: Generate webpages with a variable number of images
# Liam Simmons Mar 2018
# Usage: gen.py <file size> <number of images> <opt: filename>

# Generates a webpage with a given image size and given number of images
# If the image size is not one of the options, defaults to 5k
# Options are: 5k,10k,100k,200k,500k,1m,10m,210m
# If the number of images is not one of the options, defaults to 1
# Options are: 1,2,5,10,100,200
# Takes an optional third parameter, the filename, otherwise creates 'test.html'


import sys

if len(sys.argv) < 3:
	print('Error: Usage gen.py <file size> <number> <opt:file name>')
	print('Exiting...')
	sys.exit()

size = sys.argv[1]
number = int(sys.argv[2])
filename = "test.html"

if len(sys.argv) >= 4:
	filename = sys.argv[3]
	if sys.argv[3].find(".html") == -1:
		filename += ".html"

sizes = ['5k','10k','100k','200k','500k','1m','10m','210m']
numbers = [1,2,5,10,100,200]

if size not in sizes:
	print('Improper file size given. Default: 5k')
	size = '5k'

if number not in numbers:
	print('Improper number given. Default: 1')
	number = 1

txt = '''<!DOCTYPE html>
<html>
<head>
	<title>Test Page</title>
</head>

<body>
	<h1>Test</h1>
	'''
img = '''<img src="media/''' + size + '''.jpg"/>\n'''
end = '''</body></html>'''

wp = open(filename,'w+')
wp.write(txt)
for i in range(number):
	wp.write(img)
wp.write(end)
wp.close()