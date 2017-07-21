from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from lxml import html
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from pymongo import MongoClient
from selenium.webdriver.support.select import Select
import time
import json
import csv
import pdb

#	Parameter Format:
#
#	{
#		"PassengerCount" : Integer,
#		"JourneyType" : Integer (0, 1),
#		"Origin" : String,
#		"Destination" : String,
#		"FromDate" : Date String (yyyy-mm-dd),
#		"ReturnDate" : Date String (yyyy-mm-dd) or Integer (SearchType = 1),
#		"SearchType" :  Integer (0, 1)
#	}
#
#	JourneyType 
#		0 : one way
#		1 : round trip
#
#	SearchType
#		0 : exact date
#		1 : monthly


# display = Display(visible=0, size=(800, 600))
# display.start()

parameters = None

result = {
	'lowest_price': None,
	'list': []
}

lowest_price = -1


driver = webdriver.Chrome(".//chromedriver")
driver.get("http://matrix.itasoftware.com/")

with open('input.json') as f:
	parameters = json.load(f)

methods = driver.find_elements_by_xpath("//div[contains(@class, 'gwt-TabBarItem')]/div[contains(@class, 'gwt-HTML')]")

active_idx = 1 - parameters['JourneyType']


# Select travel method according to Journey Type 

methods[active_idx].click()


# Find all required fields

container = driver.find_element_by_xpath('//div[@class="gwt-TabPanelBottom"]')
active_container = container.find_elements_by_xpath('./div')[active_idx]

from_location = active_container.find_element_by_xpath('.//label[text()=" Departing from "]/../div//input')
to_location = active_container.find_element_by_xpath('.//label[text()=" Destination "]/../div//input')
fromdate = retdate = None

if parameters['SearchType']:
	active_container.find_element_by_xpath('.//label[text()="See calendar of lowest fares"]').click()

if parameters['JourneyType'] == 0: # One way
	if parameters['SearchType'] == 0: # Normal Search
		fromdate = active_container.find_element_by_xpath('.//div[text()="Departure Date"]/../div/input')
	else: # Monthly
		fromdate = active_container.find_element_by_xpath('.//label[text()=" Departing "]/../div/input')
else:
	if parameters['SearchType'] == 0:
		fromdate = active_container.find_element_by_xpath('.//div[text()="Outbound Date"]/../div/input')
		retdate = active_container.find_element_by_xpath('.//div[text()="Return Date"]/../div/input')
	else:
		fromdate = active_container.find_element_by_xpath('.//label[text()=" Departing "]/../div/input')
		retdate = active_container.find_element_by_xpath('.//label[text()=" Length of stay "]/../div/input')

passengercount = Select(active_container.find_element_by_xpath('//label[text()=" Adults "]/../div//select'))

searchbutton = driver.find_element_by_xpath('//button[@id="searchButton-0"]')


def save_result():
	global result

	print "TOTAL : " + str(len(result['list'])) + "  saved"

	with open('out.json', 'w') as f:
		f.write(json.dumps(result))


# Exit 
def exit_script():
	save_result()
	try:
		driver.close()

		display.stop()

		# display.popen.terminate()
		display.popen.kill()
	except:
		pass

	exit(0)

#blur listing
def blur_listing():
	try:
		driver.find_element_by_xpath('//div[@class="footer"]').click()
	except:
		pass

# Wait until result loads
def wait_load():
	repeat = 10
	while repeat != 0:
		try:
			time.sleep(1)
			element = WebDriverWait(driver, 10).until(EC.invisibility_of_element_located((By.XPATH, '//img[@class="IR6M2QD-n-b"]')))
			time.sleep(1)
			break
		except:
			print "Waiting for load"
			pass
		repeat = repeat - 1

	if repeat == 0:
		print "Load timeout"
		driver.close()
		exit_script()
	blur_listing()

# Get results in listing page
def get_page_list():

	global lowest_price
	global result

	try:
		print "Wait for loading Listing page"
		wait_load()
		# If pagination exists show all by clicking 'All' button
		all_btn = driver.find_element_by_xpath('//a[text()="All"]').click()
		print "Loading all flights list"
		wait_load()
	except:
		pass

	print "Page Loaded"

	items = driver.find_elements_by_xpath('//span[text()="Details"]/../../..')

	for item in items:
		source = html.fromstring(item.get_attribute('innerHTML'))
		
		json_item = {}
		json_item['price'] = ''.join(source.xpath('//button//text()'))
		json_item['ariline'] = ' '.join(source.xpath('//tr[1]/td[1]//text()'))
		json_item['flights'] = []
		idx = 2
		price = int(json_item['price'].replace('US','').replace('*','').replace(',','').replace('$',''))
		if lowest_price == -1 or lowest_price > price:
			lowest_price = price
		for tr in source.xpath('//tr'):
			flight_item = {}
			flight_item['dep_time'] = tr.xpath('./td['+str(idx)+']//text()')[0]
			flight_item['arr_time'] = tr.xpath('./td['+str(idx+1)+']//text()')[0]
			flight_item['duration'] = tr.xpath('./td['+str(idx+2)+']//text()')[0]
			flight_item['origin'] = tr.xpath('./td['+str(idx+3)+']//span[1]/text()')[0]
			flight_item['destination'] = tr.xpath('./td['+str(idx+3)+']//span[2]/text()')[0]
			json_item['flights'].append(flight_item)
			idx = idx - 1

		result['list'].append(json_item)

	result['lowest_price'] = 'US$' + str(lowest_price)

	print str(len(result['list'])) + "  Collected"

	save_result()

	if len(result['list']) > parameters['limit'] and parameters['SearchType'] == 1:
		exit_script()


# Feed fields with parameters

from_location.send_keys(parameters['Origin'])
to_location.send_keys(parameters['Destination'])
fromdate.send_keys(parameters['FromDate'] + Keys.TAB)
if parameters['JourneyType']:
	retdate.send_keys(parameters['ReturnDate'] + Keys.TAB)
passengercount.select_by_index(parameters['PassengerCount'] - 1)

wait_load()

from_location.send_keys(Keys.RETURN)


if parameters['SearchType'] == 0:
	get_page_list()
else:
	print "Wait for loading month page"
	wait_load()
	days = driver.find_elements_by_xpath("//div[contains(text(), '$')]/..")
	for idx in range(0, len(days)):
		print "Getting " + str(idx) + " day page"
		days[idx].click()
		get_page_list()
		driver.execute_script("window.history.go(-1)")
		print "Navigate back"
		wait_load()
		days = driver.find_elements_by_xpath("//div[contains(text(), '$')]/..")

exit_script()
