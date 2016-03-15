# Box #
It's some scraps metal box. Drilled holes and square to fit electronic in it. It contains :
  * arduino duemilanove http://arduino.cc/
  * wi-fi shield (sparkfun wifly shield). It could be any ethernet shield (but that would require few changes) https://www.sparkfun.com/products/9954 I have re-written the sparkfun library using arduino provided SPI lib http://radio-box.googlecode.com/files/Wifly.zip
  * a 4 x 20 character screen (using i2c) http://www.robotshop.com/world/devantech-lcd03-4x20-serial-lcd-blue.html
  * 2 toggle switches (to choose between radio/podcast/files modes) https://www.sparkfun.com/products/9276
  * 2 push buttons (select/cancel) https://www.sparkfun.com/products/9180
  * an incremental rotary encoder http://www.robotshop.com/world/productinfo.aspx?pc=RB-Plx-218&lang=en-US
  * AC converter that outputs 12V 1.25A. Most current consumption actually comes from the wi-fi module (up to 0.75 according to doc)

# Server #
  * a pc linked to loud speakers or hifi. Could be an old pc, a desktop or a backup system (that already contains music !)
  * Linux (Ubuntu 12.10)
  * python
`sudo apt-get install python`
  * gstreamer with pyGst. Gstreamer is by default on Ubuntu. These are for support of pyGst and diverse stream source and codec
`sudo apt-get install python-gtk2 gstreamer0.10-gnomevfs gstreamer0.10-fluendo-mp3 gstreamer0.10-plugins-bad gstreamer0.10-plugins-ugly`
  * xsltproc to extract episode list from podcast http://xmlsoft.org/XSLT/xsltproc.html. Bash podder helped a lot to find and understand xsltproc http://lincgeek.org/bashpodder/ http://en.wikipedia.org/wiki/XSLT
`sudo apt-get install xsltproc`