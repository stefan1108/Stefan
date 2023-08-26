import framebuf
import machine
import ssd1306
import sys
import time
from onewire import OneWire
from ds18x20 import DS18X20

import config
import freesans20
import writer
'''
--------------------------------------------------
Mein erstes größeres PICO Projekt
--------------------------------------------------
Dieses Projekt wurde realisiert um nicht unnötig
Warmwasser zirkulieren zu lassen
->Energieersparnis von Heizöl

Es wurde relativ offen gehalten, das heißt man hat
insgesamt 6 Eingänge für Sensoren über die Wago-
Klemmen (bitte nur Orginale 60 221-2411 verwenden),
sowie ein Relai zum Schalten großer Lasten.
Zukünftig wären verschiedene Grundkörper konstruierbar,
mit mehr Klemmen oder mehr Relais.
Gerne mich anschreiben :-)
'''

# Echtzeituhr im Mikrocontroller initialisieren
rtc = machine.RTC()
rtc.datetime((2020, 1, 1, 1, 0, 0, 0, 0))#auf den 1.1.2020 setzen


#global datetime #globaler Datetime, um mit infos aus Datum und Uhrzeit arbeiten zu können
#datetime = rtc.datetime()

#print (rtc.datetime())
#print('Aktuelle Uhrzeit: %02d:%02d' % (datetime[4], datetime[5]))

#anlegen zum Rechnen (für Zeitschaltung OHNE time.sleep
start=time.ticks_ms()
start_temp=time.ticks_ms()

#Defination aller Ein- und Ausgänge:

adc0_JoyY=machine.ADC(config.ANALOG_JOY_Y)
adc1_Joyx=machine.ADC(config.ANALOG_JOY_X)

eTaster=machine.Pin(config.eTaster,machine.Pin.IN,machine.Pin.PULL_UP)
aRelai=machine.Pin(config.aRelai,machine.Pin.OUT)

# Initialisierung GPIO für OneWire und DS18B20
one_wire_bus = machine.Pin(config.one_wire_bus)
sensor_ds = DS18X20(OneWire(one_wire_bus))

# One-Wire-Geräte ermitteln
devices = sensor_ds.scan()
#print(devices)

#Merker für Displaysteuerung
display_on_off = 0


global temperature_Diff  #Variable für Temperatursteuerung (später noch veränderbar)
temperature_Diff=10

def _init_display():
    global display
    global font_writer
    global display_on_off

    i2c = machine.I2C(1, scl=machine.Pin(config.DISPLAY_SCL_PIN),
                      sda=machine.Pin(config.DISPLAY_SDA_PIN),freq=400000, timeout=50000)
    if 60 not in i2c.scan():
        raise RuntimeError('Cannot find display.')
    
    display = ssd1306.SSD1306_I2C(128, 64, i2c)
    font_writer = writer.Writer(display, freesans20)
    display_on_off=1

def load_image(filename):
    with open(filename, 'rb') as f:
        f.readline()
        width, height = [int(v) for v in f.readline().split()]
        data = bytearray(f.read())
    return framebuf.FrameBuffer(data, width, height, framebuf.MONO_HLSB)

def anzeige(temperature_Boiler, temperature_Leitung,einstellung):
    global display_on_off
    global datetime
    global temperature_Diff

    display.fill(0)
    
    if temperature_Boiler==-1 and temperature_Leitung==-1:
        display.poweroff()
        display_on_off=0
        return
    if display_on_off == 0:
        _init_display()
        #display_on_off=1
    #print("anzeige: ")
    #print(einstellung)
    if einstellung<1:
        einstellung=einstellung*-1
        einst_pbm = load_image('einstellung.pbm')
        display.blit(einst_pbm, 64, 50)
    
    if einstellung==0:
        screen_pbm = load_image('screen.pbm')
        display.fill(0)
        display.blit(screen_pbm, 0, 0)
        display.show()
        temp_thread()
        display.fill(0)
        display.rect(0, 0, 128, 64, 1)
        display.line(64, 0, 64, 64, 1)
        display.text("Boiler:",5,10)
        display.text("Leitung",65,10)
    
        text = '{:.1f}'.format(temperature_Boiler)
        textlen = font_writer.stringlen(text)
        font_writer.set_textpos((64 - textlen) // 2, 30)
        font_writer.printstring(text)

        text = '{:.1f}'.format(temperature_Leitung)
        textlen = font_writer.stringlen(text)
        font_writer.set_textpos(64 + (64 - textlen) // 2, 30)
        font_writer.printstring(text)
       
    if einstellung==1:#Uhrzeit anzeige
        display.text("Aktuelle Uhrzeit",0,10)
        display.rect(64, 35, 2, 2, 1)
        display.rect(64, 42, 2, 2, 1)
        
        
        text = '{:02d}'.format(datetime[4])
        textlen = font_writer.stringlen(text)
        font_writer.set_textpos((64 - textlen) // 2, 30)
        font_writer.printstring(text)

        text = '{:02d}'.format(datetime[5])
        textlen = font_writer.stringlen(text)
        font_writer.set_textpos(64 + (64 - textlen) // 2, 30)
        font_writer.printstring(text)
        #display.numbers(datetime[4], datetime[5])
        #display.text(time.localtime([3]),0,30)
        #display.text(time.localtime([3]),0,30)
        
        
    
    if einstellung==2:
        display.text("Differenztemp",0,10)
        text = '{:.1f}'.format(temperature_Diff)
        textlen = font_writer.stringlen(text)
        font_writer.set_textpos((64 + textlen) // 2, 30)
        font_writer.printstring(text)
    #print('Aktuelle Uhrzeit: %02d:%02d' % (datetime[4], datetime[5]))
    #print(rtc.datetime())
    display.show()
    

def temp_thread():
    global temperature_Boiler
    global temperature_Leitung
    
    # Temperatur messen
    sensor_ds.convert_temp()
    # Warten: min. 750 ms
    time.sleep_ms(750)
    # Sensoren abfragen
    temperature_Boiler= sensor_ds.read_temp(devices[0])
    temperature_Leitung = sensor_ds.read_temp(devices[1])
    
temp_thread()
_init_display()
einstellung=0
        
while True:
    global temperature_Boiler
    global temperature_Leitung
    global temperature_Diff
    JoyY = adc0_JoyY.read_u16()
    JoyX = adc1_Joyx.read_u16()
    datetime = rtc.datetime()
    if JoyY>45000 or JoyY<15000:#normale anzeige immer reset auf fenster 0
        print('JoyY:', JoyY)
        print('JoyX:', JoyX)        
        print('Temperature_Boiler = {temperature_Boiler}, temperature_Leitung = {temperature_Leitung}'.format(temperature_Boiler=temperature_Boiler, temperature_Leitung=temperature_Leitung))
        start=time.ticks_ms()#reset standby zeit
        #print(start)
        anzeige(temperature_Boiler, temperature_Leitung,einstellung)
        print(einstellung)
    if time.ticks_diff(time.ticks_ms(), start) > 60000:#1Minute anzeige 
        anzeige(-1,-1,einstellung)
        einstellung=0
    if time.ticks_diff(time.ticks_ms(), start_temp) > 30000:#alle 30 sec Temperaturmessung
        start_temp=time.ticks_ms()
        temp_thread()
    if (JoyX>65000 or JoyX<1000) and einstellung>=0:#umschaltung fenster
        einstellung += (JoyX-30000)//33000
        if einstellung>2:
            einstellung=0
        if einstellung<0:
            einstellung=2
        start=time.ticks_ms()#reset standby zeit
        anzeige(temperature_Boiler, temperature_Leitung,einstellung)
        time.sleep_ms(200)
    if temperature_Boiler>(temperature_Leitung+temperature_Diff) and (datetime[4]>19 or (datetime[4]>18 and datetime[5]>29)) and datetime[4]<22:#zwischen 19:30 und 22 Uhr einschaltbar
        aRelai.value(1)
    else:
        aRelai.value(0)
    if  einstellung==-2 and (JoyY>35000 or JoyY<25000):#einstellung Temperaturdiff
        temperature_Diff -= ((JoyY/10000-3)**3)/200
        #anzeige(temperature_Boiler, temperature_Leitung,einstellung)
        time.sleep_ms(50)
    if eTaster.value()==0:#taster umschaltung einstellen
        einstellung=einstellung*-1
        anzeige(temperature_Boiler, temperature_Leitung,einstellung)
        time.sleep_ms(300)
    if einstellung == -1 and (JoyY>35000 or JoyY<25000):#einstellung Zeit
        minute = datetime[5]
        hour = datetime[4]
        if JoyY>55000:
            minute=minute-5
        if JoyY<5000:
            minute=minute+5
        if JoyY<25000:
            minute=minute+1
        if JoyY>35000:
            minute=minute-1
        if minute<0:
            hour=hour-1
            minute=59
        if minute>59:
            hour=hour+1
            minute=0
        if hour>23:
            hour=0
        if hour<0:
            hour=23
        rtc.datetime((datetime[0], datetime[1], datetime[2], datetime[3], hour, minute, 0, 0))
        print(rtc.datetime())
        print('Aktuelle Uhrzeit: %02d:%02d:%02d' % (datetime[4], datetime[5],datetime[6]))
        time.sleep_ms(100)
    if einstellung<0:#dauerhafte Anzeige wenn im Einstellungsmodus
        anzeige(temperature_Boiler, temperature_Leitung,einstellung)