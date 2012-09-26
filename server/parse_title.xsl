<?xml version="1.0"?>
<stylesheet version="1.0"
	xmlns="http://www.w3.org/1999/XSL/Transform">
	<output method="text"/>
	<template match="/">
		<apply-templates select="/rss/channel/item"/>
	</template>
	<template match="item">
		<value-of select="title"/><text>:-:</text>
		<value-of select="pubDate"/><text>:-:</text>
		<text></text><value-of select="enclosure/@url"/><text>&#10;</text>
	</template>
</stylesheet>
