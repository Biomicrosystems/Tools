#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pygame
import re
import os
import math
import time
import threading
import numpy as np
from scipy.interpolate import griddata
from scipy.stats import linregress
from pygame.locals import *
import glob
import csv
from time import time
from colour import Color
from os import listdir
import subprocess
import signal
from bonotesPrincipales import *
from Adafruit_AMG88xx import Adafruit_AMG88xx
import spidev
from time import sleep
from lib_tft24T import TFT24T
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#Variables TouchScreen
DC = 24
RST = 25
LED = 15
PEN = 26

TFT = TFT24T(spidev.SpiDev(), GPIO)
##Initialize display and touch.
TFT.initTOUCH(PEN)

calib_scale240 = float(240)/3788   # Likely about 285
calib_scale320 = float(320)/3777   # Likely about 384
calib_offset240 = calib_scale240 * 180   # Likely about 28
calib_offset320 = calib_scale320 * 318   # Likely about 25

# Variables del sistema
salirMainScrn = False
corriendoMainScrn = False
salir = False
imprimirTem = True

grabandoCSV = False
salirGrabacionCSV = True

grabandoVideo = False
grabarVideo = False

configurar = False
configurando = False

confiMax = False

confiMin = False

confiCal = False
configurandoCal = False

tomaHabilitada = True
calX = []
calY = []

promedioTem = 0
promedioDatos = 0

box_active = False
input_box = pygame.Rect(79, 185, 82, 31)

color_inactive = (0,0,0)
color_active = pygame.Color('dodgerblue2')


csv_pixels = []
tiempo_inicio_csv = time()
#low range of the sensor (this will be blue on the screen)
MINTEMP = 30

#high range of the sensor (this will be red on the screen)
MAXTEMP = 40
fileNameLimits = 'source/colorLimits.txt'
fileNameCalibration = 'source/calibration.txt'

try:
    colorFile = open(fileNameLimits,'r')
    colorStr = colorFile.read().split(",")
    colorInt = [int(x) for x in colorStr]
    MINTEMP = colorInt[0]
    MAXTEMP = colorInt[1]
except:
    print("Color por defecto")



#how many color values we can have
COLORDEPTH = 1024

nPixels = 64

os.putenv('SDL_FBDEV', '/dev/fb1')
pygame.init()

#initialize the sensor
sensor = Adafruit_AMG88xx()

points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0, 64)]
grid_x, grid_y = np.mgrid[0:7:32j, 0:7:32j]


#Screen is 240x320
scrn_height = 240
scrn_width = 320

#sensor is an 8x8 grid so lets do a square
map_height = min(scrn_height,scrn_width)
map_width = min(scrn_height,scrn_width)

#the list of colors we can choose from
blue = Color("indigo")
colorsList = list(blue.range_to(Color("red"), COLORDEPTH))
FONDO = (32, 30, 32)
BLANCO = (255, 255, 255)
COLOR_TEXTO = (50, 60, 80)
GRIS =(211,211,211)
AZUL = (42, 39, 96)
NEGRO = (0,0,0)

#create the array of colors
colors = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255)) for c in colorsList]
# colorsTrans = [(int(c.red * 255), int(c.green * 255), int(c.blue * 255), 50) for c in colorsList]
displayPixelWidth = map_width / 8
displayPixelHeight = map_height / 8

displayPixelWidthCubic = float(map_width) / 30
displayPixelHeightCubic = float(map_height) / 30

#Linealization parameters
xParameter = 0.2959
bParameter = -2.4836
try:
    calibrationFile = open(fileNameCalibration,'r')
    calibrationStr = calibrationFile.read().split(",")
    calibrationInt = [float(x) for x in calibrationStr]
    xParameter = calibrationInt[0]
    bParameter = calibrationInt[1]
except:
    print("Calibración por defecto")


click = False
##################################################################   Botones principales  #####################################################################
def posBotonRec(pos, dim):
    rec = (pos[0]-dim[0]/2,pos[1]-dim[1]/2 , dim[0], dim[1])
    return rec

def posBotonEsquina(pos, dim):
    rec = [pos[0]-dim[0]/2, pos[1]-dim[1]/2]
    return rec


tam_boton = (scrn_width - map_width)/2
botones=[]
bonotesMAinScreen(pygame, botones)

botonesConfig = []
botonesSettingScreen(pygame, botonesConfig)


botonesMaximo = []
botonesLimScreen(pygame, botonesMaximo)

botonesCalibracion = []
botonesCalScreen(pygame, botonesCalibracion)

##########################################################################################################################################################


#Se crea la pantalla que contendra la interfaz
flags = pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.RESIZABLE | pygame.SRCALPHA
lcd = pygame.display.set_mode((scrn_width, scrn_height), flags)
pygame.display.set_caption('Cámara Térmica')
textFont = pygame.font.SysFont("comicsansms", int(displayPixelWidth/2))
textFont_botones = pygame.font.SysFont("comicsansms", int(tam_boton/3))
textFont_temp = pygame.font.SysFont("comicsansms", int(displayPixelWidth/2))
textFont_rango_confi = pygame.font.SysFont("comicsansms", 60)
textFont_rango_cal = pygame.font.SysFont("comicsansms",40 )
textFont_titulo = pygame.font.SysFont("comicsansms", 30)
pygame.display.toggle_fullscreen()
lcd.fill(BLANCO)
pygame.display.update()

directorios = listdir("/media/pi")
if len(directorios)>0:
    raiz = "/media/pi/" + directorios[0] +"/"
else:
    raiz ="/home/pi/Documents/"

raiz ="/home/pi/Documents/"

#Funciones
#Guardar variables tlimites
def guardarVariables(var1, var2, archivo):
    file = open(archivo,"w")
    text = str(var1) + "," + str(var2)
    file.write(text)
    file.close()


def regLineal(datX, datY):
    regresion = linregress(datX, datY)
    pendiente = regresion.slope
    corte = regresion.intercept
    return pendiente,corte


def actualizarTemCal(var):
    global text_recV
    var = round(var,2)
    posMenos = botonesCalibracion[2]['pos']
    posMas = botonesCalibracion[3]['pos']
    colorText = color_active if box_active else color_inactive
    textLabelVar = textFont_rango_cal.render(str(var), True, colorText)
    text_recV = textLabelVar.get_rect()
    text_recV.center = ((posMenos[0] + posMas[0]) / 2, (posMenos[1] + posMas[1]) / 2)
    pygame.draw.rect(lcd, BLANCO, input_box)
    lcd.blit(textLabelVar, text_recV)



def dibujar_botones_calibracion():
    lcd.fill(BLANCO)
    for boton in botonesCalibracion:
        if boton['habilitado']:
            lcd.blit(boton['imagen'], boton['rect'])
        else:
            lcd.blit(boton['imagen_dos'], boton['rect'])

    texto = "Calibracion"
    textFont_titulo = pygame.font.SysFont("comicsansms", 20)
    textLabel = textFont_titulo.render(texto, True, NEGRO)
    text_rec =  textLabel.get_rect()
    text_rec.center = (120, 25)
    lcd.blit(textLabel, text_rec)

def dibujarBarraColor(posHorizontal):
    widthBar = 10
    heightBar = scrn_height
    for i in range(heightBar):
        pygame.draw.rect(lcd, colors[int(i*4)],(posHorizontal+1, heightBar-i, widthBar, 2))
    rango = MAXTEMP - MINTEMP
    nTxtBar = 5
    tam_marcas = rango/float(nTxtBar-1)
    tam_marcas_pixel = map_height/(nTxtBar-1)
    for i in range(nTxtBar):
        txtBar = "- "+str(int(MINTEMP+int(tam_marcas*i)))
        textLabel = textFont_temp.render(txtBar, True, NEGRO)
        lcd.blit(textLabel, (posHorizontal + 12, map_height - tam_marcas_pixel*i -int(displayPixelWidth/3)))
    txt = "- "+str(MAXTEMP)
    textLabel = textFont_temp.render(txt, True, NEGRO)
    lcd.blit(textLabel, (posHorizontal + 12, 1))

def dibujar_botones_configuracion():
    for boton in botonesConfig:
        rec = posBotonRec(boton['pos'], (85,85))
        pygame.draw.rect(lcd, AZUL, rec)
        lcd.blit(boton['imagen'], boton['rect'])
        textLabel = textFont_temp.render(boton['texto'][0], True, BLANCO)
        lcd.blit(textLabel, (rec[0]+5, rec[1]+rec[3] - 12))

def dibujar_botones_rango(texto, var):
    lcd.fill(GRIS)
    for boton in botonesMaximo:
        lcd.blit(boton['imagen'], boton['rect'])

    posMenos = botonesMaximo[0]['pos']
    posMas = botonesMaximo[1]['pos']
    textLabelVar = textFont_rango_confi.render(str(var), True, NEGRO)
    text_recV = textLabelVar.get_rect()
    text_recV.center = ((posMenos[0] + posMas[0]) / 2, (posMenos[1] + posMas[1]) / 2)
    lcd.blit(textLabelVar, text_recV)

    textLabel = textFont_titulo.render(texto, True, NEGRO)
    text_rec =  textLabel.get_rect()
    text_rec.center = (180, 25)
    lcd.blit(textLabel, text_rec)

def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def dibujar_botones_iniciales(lista_botones):
    lcd.fill(BLANCO)
    for boton in lista_botones:
        if boton['selected']:
            lcd.blit(boton['imagen_dos'], boton['rect'])
            textBoton = boton['texto2']
        else:
            lcd.blit(boton['imagen'], boton['rect'])
            textBoton = boton['texto1']
        for i in range(len(textBoton)):
            texto=textBoton[i]
            textLabel = textFont_botones.render(texto, True, NEGRO)
            lcd.blit(textLabel, (scrn_width - tam_boton - 2,boton['rect'][1]-10 + (i*displayPixelWidth/3))  )
    dibujarBarraColor(map_width)

def cerrarTodo():
    global confiCal, configurar, grabarVideo, salirGrabacionCSV, salir
    confiCal = configurar = grabarVideo = False
    salirGrabacionCSV = salir = True


def interfaz():
    global salir, map_height, map_width, displayPixelWidth, displayPixelHeight, lcd, botones, salirGrabacionCSV, grabarVideo, configurar, confiCal, box_active, promedioTem
    text = "0"
    while not salir:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cerrarTodo()
                quit()
            if event.type == MOUSEBUTTONUP:
                mouse = event.pos
                if input_box.collidepoint(event.pos) and not tomaHabilitada:
                    # Toggle the active variable.
                    box_active = True
                else:
                    box_active = False
                # Change the current color of the input box.

                presionarPantalla(mouse)
            text = "0" if tomaHabilitada else text
            if event.type == pygame.KEYDOWN:
                # Permite terminar el programa
                if event.key == pygame.K_q:
                    cerrarTodo()
                # Alterna entre 'pantalla completa' y 'ventana'.
                elif event.key == pygame.K_f:
                    pygame.display.toggle_fullscreen()
                elif not tomaHabilitada and box_active:
                    if event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    else:
                        if not re.match(r'^-?\d+(?:\.\d+)?$', event.unicode) is None or event.unicode == ".":
                            text += event.unicode
                    try:
                        text = "0" if text == "" else text
                        print(text)
                        promedioTem = float(text)
                    except Exception as e:
                        print(e)

        pygame.time.wait(10)

def botonesPantallaConfiguracion():
    global salirGrabacionCSV, grabarVideo, botones, configurar, salirMainScrn, confiMax, MAXTEMP, MINTEMP, confiMin, salir, confiCal
    if botonesConfig[0]['selected']:
        confiMax = True
    elif botonesConfig[1]['selected']:
        confiCal = True
    elif botonesConfig[2]['selected']:
        configurar = salirMainScrn = botones[2]['selected'] = botonesConfig[2]['selected'] = False
    elif botonesConfig[3]['selected']:
        confiMin = True
    elif botonesConfig[4]['selected']:
        configurar = grabarVideo = False
        salirGrabacionCSV = salir = True
        pygame.time.wait(200)
        subprocess.Popen("shutdown -h now", shell=True)
    for boton in botonesConfig:
        boton['selected'] = False

def botonesConfiMax():
    global salirGrabacionCSV, grabarVideo, botones, configurar, salirMainScrn, confiMax, MAXTEMP, MINTEMP, confiMin, salir, confiCal
    if botonesMaximo[0]['selected']:
        MAXTEMP = constrain(MAXTEMP + 1, MINTEMP + 1, 100)
    elif botonesMaximo[1]['selected']:
        MAXTEMP = constrain(MAXTEMP - 1, MINTEMP + 1, 100)
    elif botonesMaximo[2]['selected']:
        guardarVariables(MINTEMP, MAXTEMP, fileNameLimits)
        confiMax = False
    for boton in botonesMaximo:
        boton['selected'] = False

def botonesConfiMin():
    global salirGrabacionCSV, grabarVideo, botones, configurar, salirMainScrn, confiMax, MAXTEMP, MINTEMP, confiMin, salir, confiCal
    if botonesMaximo[0]['selected']:
        MINTEMP = constrain(MINTEMP + 1, 0, MAXTEMP - 1)
    elif botonesMaximo[1]['selected']:
        MINTEMP = constrain(MINTEMP - 1, 0, MAXTEMP - 1)
    elif botonesMaximo[2]['selected']:
        guardarVariables(MINTEMP, MAXTEMP, fileNameLimits)
        confiMin = False
    # dibujar_botones_rango("Tope temperatura maxima", MAXTEMP)
    for boton in botonesMaximo:
        boton['selected'] = False

def botonesConfiCal():
    global salirGrabacionCSV, grabarVideo, botones, configurar, salirMainScrn, confiMax, MAXTEMP, MINTEMP, confiMin, salir, confiCal, promedioTem, tomaHabilitada, xParameter, bParameter, calY, calX
    if botonesCalibracion[0]['selected']:
        xParameter, bParameter = regLineal(calX, calY)
        guardarVariables(xParameter, bParameter, fileNameCalibration)
    elif botonesCalibracion[1]['selected']:
        calX = []
        calY = []
        confiCal = False
    elif botonesCalibracion[2]['selected']:
        promedioTem -= 0.1
    elif botonesCalibracion[3]['selected']:
        promedioTem += 0.1
    elif botonesCalibracion[4]['selected']:
        if not tomaHabilitada:
            calX.append(int(promedioDatos))
            calY.append(promedioTem)
        tomaHabilitada ^= 1
        for bot in range(2,6):
            botonesCalibracion[bot]['habilitado'] ^= 1
        if len(calX) >= 2:
            botonesCalibracion[0]['habilitado'] = True
    elif botonesCalibracion[5]['selected']:
        tomaHabilitada ^= 1
        for bot in range(2,6):
            botonesCalibracion[bot]['habilitado'] ^= 1
    for boton in botonesCalibracion:
        boton['selected'] = False

def presionarPantalla(mouse):
    global salirGrabacionCSV, grabarVideo, botones, configurar, salirMainScrn, confiMax, MAXTEMP, MINTEMP, confiMin, salir, confiCal, click
    scrnConfi = confiMax or confiMin or confiCal
    if corriendoMainScrn:
        for boton in botones:
            boton['selected'] = boton['selected'] ^ boton['rect'].colliderect([mouse[0]-1, mouse[1], 1, 1])
        salirGrabacionCSV = not botones[1]['selected']
        grabarVideo = botones[0]['selected']
        configurar = botones[2]['selected']
        if not configurar:
            dibujar_botones_iniciales(botones)
    elif configurando and not scrnConfi:
        for boton in botonesConfig:
            boton['selected'] = boton['rect'].colliderect([mouse[0] - 1, mouse[1], 1, 1])
        botonesPantallaConfiguracion()
    elif confiMax:
        for boton in botonesMaximo:
            boton['selected'] = boton['rect'].colliderect([mouse[0] - 1, mouse[1], 1, 1])
        botonesConfiMax()
    elif confiMin:
        for boton in botonesMaximo:
            boton['selected'] = boton['rect'].colliderect([mouse[0] - 1, mouse[1], 1, 1])
        botonesConfiMin()
    elif confiCal:
        for boton in botonesCalibracion:
            boton['selected'] = boton['rect'].colliderect([mouse[0] - 1, mouse[1], 1, 1]) and boton['habilitado']
        botonesCalibracion[4]['selected'] = botonesCalibracion[4]['rect'].colliderect([mouse[0] - 1, mouse[1], 1, 1])
        botonesConfiCal()
    click = True


def mainSrcn():
    global corriendoMainScrn, csv_pixels
    corriendoMainScrn = True
    dibujar_botones_iniciales(botones)
    while not salirMainScrn:

        #read the pixels
        try:
            pixelsMap = sensor.readPixels()
            # pixelsMap = np.random.rand(64,1)*100
            pixels = [map(p, MINTEMP, MAXTEMP, 0, COLORDEPTH - 1) for p in pixelsMap]

            if botones[3]['selected']:
                for ix in range(8):
                    for jx in range(8):
                        pygame.draw.rect(lcd, colors[constrain(int(pixels[ix * 8 + jx]), 0, COLORDEPTH - 1)], (displayPixelHeight * ix, displayPixelWidth * jx, displayPixelHeight, displayPixelWidth))
                        textTemp = textFont.render(str(round((pixelsMap[ix * 8 + jx] / 0.25) * xParameter +bParameter, 2)), True, (255, 255, 255))
                        textTempRec = textTemp.get_rect()
                        textTempRec.center = ( int( displayPixelHeight * (ix+0.5) ) , int( displayPixelWidth * (jx + 0.5) ))
                        lcd.blit(textTemp, textTempRec)
            else:
                # perdorm interpolation
                bicubic = griddata(points, pixels, (grid_x, grid_y), method='cubic')

                # draw everything
                for ix, row in enumerate(bicubic):
                    for jx, pixel in enumerate(row):
                        pygame.draw.rect(lcd, colors[constrain(int(pixel), 0, COLORDEPTH - 1)], (7.5 * ix, 7.5 * jx, displayPixelHeightCubic, displayPixelWidthCubic))
            if grabandoCSV:
                tiempo_actual_csv = time() -tiempo_inicio_csv
                pixelsMap.insert(0,tiempo_actual_csv)
                csv_pixels.append(pixelsMap)

            if not salirMainScrn:
                pygame.display.update()
        except Exception as e:
            print(e)
    corriendoMainScrn = False

x_file_csv = 0
def grabar_csv():
    global grabandoCSV, x_file_csv,tiempo_inicio_csv, csv_pixels
    tiempo_inicio_csv = time()
    grabandoCSV = True
    dir = listdir(raiz)
    if not "csvFiles" in dir:
        try:
            os.system("mkdir " +raiz+ "csvFiles")
        except Exception as e:
            print(e)

    filename = raiz +"csvFiles/camara_termica.csv"
    if not raiz + "csvFiles/camara_termica" + str(x_file_csv) + ".csv" in glob.glob(raiz +"csvFiles/*.csv"):
        filename =raiz + "csvFiles/camara_termica" + str(x_file_csv) + ".csv"
    else:
        x_file_csv += 1
        grabar_csv()
    archivo = open(filename, "w")
    csv_escritor = csv.writer(archivo)
    #Encabezado del archivo
    text_header = ["Tiempo"]
    for i in range(nPixels):
        text_header.append("Pixel "+ str(i))
    csv_escritor.writerow(text_header)
    archivo.close()

    while not salirGrabacionCSV:
        archivo = open(filename, "a")
        csv_escritor = csv.writer(archivo)
        for i in range(len(csv_pixels)):
            csv_escritor.writerow(csv_pixels[i])
        csv_pixels = []
        archivo.close()
        pygame.time.wait(1000)
    grabandoCSV = False

x_file_video = 0
def iniciarGrabarVideo():
    global p, grabandoVideo, x_file_video
    grabandoVideo = True
    filename = raiz + "videoFiles/camara_termica" + str(x_file_video) + ".mkv"
    dir = listdir(raiz)
    if not "videoFiles" in dir:
        try:
            os.system("mkdir " +raiz+ "videoFiles")
        except Exception as e:
            print(e)
    if not raiz +"videoFiles/camara_termica" + str(x_file_video) + ".mkv" in glob.glob(raiz +"videoFiles/*.mkv"):
        filename = raiz +"videoFiles/camara_termica" + str(x_file_video) + ".mkv"
    else:
        x_file_video += 1
        iniciarGrabarVideo()
    comando = "ffmpeg -f alsa -r 10 -f x11grab -s $(xdpyinfo | grep dimensions | awk '{print $2;}') -i ${DISPLAY} -c:v libx264rgb -crf 0 -preset:v ultrafast -af aresample=async=1:first_pts=0 "+ filename
    p = subprocess.Popen(comando, shell=True, stdin=None, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, close_fds=True)

def detenerVideo():
    global p, grabandoVideo
    os.killpg(os.getpgid(p.pid), signal.SIGINT)
    grabandoVideo = False

def touchScreen():
    press = False
    mouse = []
    while not salir:
        while not TFT.penDown() and not salir:
            if press:
                presionarPantalla(mouse)
            press = False
            pygame.time.wait(10)
        x = TFT.readValue(TFT.X)
        y = TFT.readValue(TFT.Y)
        x2 = int(y * calib_scale320 - calib_offset320)
        y2 = int(x * calib_scale240 - calib_offset240)
        mouse = [x2, y2]
        press = True

def configuracionPantalla():
    global salirMainScrn, configurando, click
    configurando = True
    salirMainScrn = True
    while configurar:
        if click:
            lcd.fill(GRIS)
            if confiMax:
                dibujar_botones_rango("Tope temperatura maxima",MAXTEMP)
            elif confiMin:
                dibujar_botones_rango("Tope temperatura minima", MINTEMP)
            elif confiCal:
                dibujar_botones_calibracion()
                dibujarBarraColor(map_width - 10)
            else:
                dibujar_botones_configuracion()
            if not confiCal:
                pygame.display.update()
            pygame.time.wait(100)
            click = False
    configurando = False

def confiCalibracion():
    global configurandoCal, configurar, promedioTem, promedioDatos
    configurandoCal = True
    pygame.display.update()
    pixelsMap = []
    while confiCal:
        try:

            if tomaHabilitada:
                pixelsMap = sensor.readPixels()
                # pixelsMap = np.random.rand(64, 1) * 100
            pixels = [map(p, MINTEMP, MAXTEMP, 0, COLORDEPTH - 1) for p in pixelsMap]
            promTem = 0
            promDatos = 0

            for ix in range(3,5):
                for jx in range(3,5):
                    pygame.draw.rect(lcd, colors[constrain(int(pixels[ix * 8 + jx]), 0, COLORDEPTH - 1)], (displayPixelHeight * ix, displayPixelWidth * jx, displayPixelHeight, displayPixelWidth))
                    promTem +=round((pixelsMap[ix * 8 + jx] / 0.25) * xParameter +bParameter, 2)
                    promDatos += pixelsMap[ix * 8 + jx] / 0.25
            if tomaHabilitada:
                promedioTem = promTem / 4
                promedioDatos = promDatos / 4
            actualizarTemCal(promedioTem)
            if confiCal:
                pygame.display.update()
        except Exception as e:
            print(e)
    configurandoCal = False

def principal():
    global salirMainScrn, salirGrabacionCSV
    threading.Thread(target=touchScreen).start()
    while not salir:
        if not salirMainScrn and not corriendoMainScrn:
            threading.Thread(target=mainSrcn).start()
        if not salirGrabacionCSV and not grabandoCSV:
            threading.Thread(target=grabar_csv).start()
        if grabarVideo and not grabandoVideo:
            iniciarGrabarVideo()
        elif not grabarVideo and grabandoVideo:
            detenerVideo()
        if configurar and not configurando:
            threading.Thread(target=configuracionPantalla).start()
        if confiCal and not configurandoCal:
            threading.Thread(target=confiCalibracion).start()
        pygame.time.wait(100)
    salirMainScrn = True
    salirGrabacionCSV = True


threading.Thread(target=interfaz).start()
threading.Thread(target=principal).start()




