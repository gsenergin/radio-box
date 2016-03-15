# Introduction #
This is the big picture of the system. It includes the protocol of communication between the box and the pc. You also may want to check out the [Dependencies](Dependencies.md)

![http://radio-box.googlecode.com/files/big_picture.png](http://radio-box.googlecode.com/files/big_picture.png)



# Protocol #
This is the protocol used for the radio-box and the server to communicate
Messages described below may have different meaning depending on the current mode
## Box to Server ##
  * radio : starts the radio
  * next : rotary encode was turned to the right
  * prev : rotary encode was turned to the left
  * podcast : starts podcast (fetch updates, display list)
  * select : select button was pushed
  * back : cancel/back button was pushed
  * browser : starts file browser (music library)
## Server to Box ##
  * radio\_name:n
  * scroll\_position:i/n
  * radio\_title:s
  * channel\_name:s
  * channel\_date:d
  * episode\_name:s
  * episode\_date:d
  * cursor:[next|prev]
## Modes ##
  * radio
  * podcast
  * podcast.episode
  * podcast.episode.playing
  * podcast.episode.paused
  * browser
  * browser.play
  * browser.pause
  * browser.play

# Modules #
## radio\_box\_server ##
## File Browser ##
## FrontEnd Watchdog ##
## Podcast Manager ##
## RadiBox Constants ##
## Stream Handler ##
## Title Monitor ##