#!/usr/bin/python

import socket
import sys
import time
import re
import os
from threading import Thread
import traceback
import math
import requests
from datetime import datetime
class GpsTracker:
	def __init__(self):
		self.localhost="0.0.0.0"
		port=int("9001")
		self.server_address = (self.localhost,port)
		self.devices=[]
		self.serviceUrl="http://127.0.0.1:9002/api/gps"
	def runserver(self):
		self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		self.server_socket.bind(self.server_address)
		print >>sys.stderr, 'Iniciando servidor en %s:%s' % self.server_address
		self.server_socket.listen(0)
		try:
			while True:
				connection, client_address = self.server_socket.accept()
				Thread(target=self.useClient, args=(connection, client_address)).start()
				#self.useClient(connection,client_address)
		except:
			self.server_socket.close()
			traceback.print_exc()
	def useClient(self, client_socket, client_address):		
		print >>sys.stderr, 'Cliente conectado:', client_address
		try:
			while True:
				client_socket.settimeout(60)
				data = client_socket.recv(1024)	
				client_socket.settimeout(None)			
				if data:
					print >>sys.stderr, 'Data recibida:  %s' % data
					if data.find('##,imei:') > -1:						
						imei = str(data[8:23])
						self.saveDevice(client_socket,imei)
						#print >>sys.stderr, 'Enviando Load'
						client_socket.sendall("LOAD")
					elif len(data)==16:
						#print >>sys.stderr, 'Enviando ON'
						client_socket.sendall("ON")
						
					elif(data.find('imei:') >-1):
						if self.analyzeData(data) != True:
							break
					else:						
						break
				else:
					break
		except:
			traceback.print_exc()
		finally:
			try:
				client_socket.close()
				print >>sys.stderr, 'Cerrando Socket ', client_address
			except:
				print >>sys.stderr, 'Error Eliminando Socket: ', client_address
	def updDevice(self, imei):
		for device in self.devices:
			if device['imei']==imei:
				device['socket'].close()
				self.devices.remove(device)
				print >>sys.stderr, 'Eliminando Socket'
				return
	def analyzeData(self, data):
		#print >>sys.stderr, 'Data recibida:  %s' % data
		rows = data.split(";")		
		for row in rows:
			cols = row.split(",")
			#print >>sys.stderr, 'Total de Columnas %s' % len(cols)
			if len(cols)>=13 and cols[4]!='L':
				imei=cols[0]
				keywork=cols[1]
				dtime=cols[2]				
				lat=cols[7]
				cord1=cols[8]
				lng=cols[9]
				cord2=cols[10]
				vel=cols[11]
				direc=cols[12]				
				#motor=cols[14]
				motor=None
				sensor=None
				#sensor=cols[16]
				fecha = self.convertDatetime(dtime)
				(clat,clong)=self.getLatlong(lat,cord1,lng,cord2)
				#print >>sys.stderr, 'Enviando a servidor bd'
				postss = requests.post(self.serviceUrl, data={'device':imei[5:],'key':keywork,'time':fecha,'lat':clat,'lng':clong,'speed':vel,'direc':direc,'acc':motor,'sensor':sensor})
				if postss.text=="false":
					#print >>sys.stderr, 'No se registro en bd'
					return False
				else:
					return True
	def convertDatetime(self, dtime):
		yy = 2000+int(dtime[:2])
		mm = dtime[2:4]
		dd = dtime[4:6]
		hh = dtime[6:8]
		minu = dtime[8:10]
		ss = dtime[10:]
		return '%s-%s-%s %s:%s:%s' % (yy,mm,dd,hh,minu,ss)
	def getLatlong(self, lat,cord1,lng,cord2):
		latd=self.convertPoint(float(lat))
		lon=self.convertPoint(float(lng))
		if cord1=='S':
			latd*=-1
		if cord2=='W':
			lon*=-1
		return (latd,lon)
	def convertPoint(self, num):
		
		ent = int(num/100)
		x = (num-(ent*100))/60
		return ent+x
	def saveDevice(self, client, imei):
		self.updDevice(imei)
		self.devices.append({'imei':imei,'socket':client})
		print >>sys.stderr, 'Registrando Dispositivo'
		#if self.devices[imei]:
		#	self.devices[imei].close()	
		#self.devices.update( {imei : client} )

if __name__ == '__main__':
	GpsTracker().runserver()