from reader import generate_tab_files
from Empire import run_empire
from scenario_random import generate_random_scenario
from datetime import datetime

########
##USER##
########

USE_TEMP_DIR = False #True
temp_dir = '/mnt/beegfs/users/stianbac' #'C:/Users/stianbac' #'/panfs/nas-0-0.local/work/stianbac'
version = 'test'
NoOfPeriods = 3
NoOfScenarios = 5
NoOfRegSeason = 2
lengthRegSeason = 168
regular_seasons = ["winter", "spring"] #, "summer", "fall"]
NoOfPeakSeason = 2
lengthPeakSeason = 24
discountrate = 0.05
WACC = 0.05
LeapYearsInvestment = 5
solver = "Gurobi" #"Xpress" # #"CPLEX"
scenariogeneration = False#True #
fix_sample = True#False #
time_format = "%d/%m/%Y %H:%M"
HEATMODULE = True #False#
DRMODULE = False#True #
LOADCHANGEMODULE = False#True #
EMISSION_CAP = True #False
IAMC_PRINT = False #True
WRITE_LP = False #True
PICKLE_INSTANCE = False #True
OUT_OF_SAMPLE = False #True
NoOfScenariosOOS = 20
filter_make = False#True #False 
filter_use = False#True #
n_cluster = 10
moment_matching = False #True
n_tree_compare = 20

#######
##RUN##
#######

name = version + '_reg' + str(lengthRegSeason) + \
    '_peak' + str(lengthPeakSeason) + \
    '_sce' + str(NoOfScenarios)
if scenariogeneration:
	name = name + "_randomSGR"
else:
	name = name + "_noSGR"
if filter_use:
    name = name + "_filter" + str(n_cluster)
if moment_matching:
    name = name + "_moment" + str(n_tree_compare)
name = name + str(datetime.now().strftime("_%Y%m%d%H%M"))
workbook_path = 'Data handler/' + version
tab_file_path = 'Data handler/' + version + '/Tab_Files_' + name
scenario_data_path = 'Data handler/' + version + '/ScenarioData'
sample_file_path = 'Data handler/' + version + '/OutOfSample'
result_file_path = 'Results/' + name
FirstHoursOfRegSeason = [lengthRegSeason*i + 1 for i in range(NoOfRegSeason)]
FirstHoursOfPeakSeason = [lengthRegSeason*NoOfRegSeason + lengthPeakSeason*i + 1 for i in range(NoOfPeakSeason)]
Period = [i + 1 for i in range(NoOfPeriods)]
Scenario = ["scenario"+str(i + 1) for i in range(NoOfScenarios)]
peak_seasons = ['peak'+str(i + 1) for i in range(NoOfPeakSeason)]
Season = regular_seasons + peak_seasons
ScenarioOOS = ["scenario"+str(i + 1) for i in range(NoOfScenariosOOS)]
Operationalhour = [i + 1 for i in range(FirstHoursOfPeakSeason[-1] + lengthPeakSeason - 1)]
HoursOfRegSeason = [(s,h) for s in regular_seasons for h in Operationalhour \
                 if h in list(range(regular_seasons.index(s)*lengthRegSeason+1,
                               regular_seasons.index(s)*lengthRegSeason+lengthRegSeason+1))]
HoursOfPeakSeason = [(s,h) for s in peak_seasons for h in Operationalhour \
                     if h in list(range(lengthRegSeason*len(regular_seasons)+ \
                                        peak_seasons.index(s)*lengthPeakSeason+1,
                                        lengthRegSeason*len(regular_seasons)+ \
                                            peak_seasons.index(s)*lengthPeakSeason+ \
                                                lengthPeakSeason+1))]
HoursOfSeason = HoursOfRegSeason + HoursOfPeakSeason
dict_countries = {"DE": "Germany", "DK": "Denmark", "FR": "France"}
    
print('++++++++')
print('+EMPIRE+')
print('++++++++')
print('HEATMODULE: ' + str(HEATMODULE))
print('DRMODULE: ' + str(DRMODULE))
print('LOADCHANGEMODULE: ' + str(LOADCHANGEMODULE))
print('Solver: ' + solver)
print('Scenario Generation: ' + str(scenariogeneration))
print('++++++++')
print('ID: ' + name)
print('++++++++')

if OUT_OF_SAMPLE:
    if DRMODULE:
        OUT_OF_SAMPLE = False
        print('Out-of-sample turned off! Cannot be used with DRMODULE')

if scenariogeneration:
    generate_random_scenario(filepath = scenario_data_path,
                             tab_file_path = tab_file_path,
                             scenarios = NoOfScenarios,
                             seasons = regular_seasons,
                             Periods = NoOfPeriods,
                             regularSeasonHours = lengthRegSeason,
                             peakSeasonHours = lengthPeakSeason,
                             dict_countries = dict_countries,
                             time_format = time_format,
                             filter_make = filter_make,
                             filter_use = filter_use,
                             n_cluster = n_cluster,
                             moment_matching = moment_matching,
                             n_tree_compare = n_tree_compare,
                             HEATMODULE = HEATMODULE,
                             LOADCHANGEMODULE = LOADCHANGEMODULE,
                             fix_sample = fix_sample)

generate_tab_files(filepath = workbook_path, tab_file_path = tab_file_path,
                   HEATMODULE = HEATMODULE, DRMODULE = DRMODULE)

run_empire(name = name, 
           tab_file_path = tab_file_path,
           result_file_path = result_file_path, 
           scenariogeneration = scenariogeneration,
           scenario_data_path = scenario_data_path,
           solver = solver,
           temp_dir = temp_dir, 
           FirstHoursOfRegSeason = FirstHoursOfRegSeason, 
           FirstHoursOfPeakSeason = FirstHoursOfPeakSeason, 
           lengthRegSeason = lengthRegSeason,
           lengthPeakSeason = lengthPeakSeason,
           Period = Period, 
           Operationalhour = Operationalhour,
           Scenario = Scenario,
           Season = Season,
           HoursOfSeason = HoursOfSeason,
           discountrate = discountrate, 
           WACC = WACC, 
           LeapYearsInvestment = LeapYearsInvestment,
           HEATMODULE = HEATMODULE,
           DRMODULE = DRMODULE, 
           IAMC_PRINT = IAMC_PRINT, 
           WRITE_LP = WRITE_LP, 
           PICKLE_INSTANCE = PICKLE_INSTANCE, 
           EMISSION_CAP = EMISSION_CAP,
           OUT_OF_SAMPLE = False,
           sample_file_path = sample_file_path,
           USE_TEMP_DIR = USE_TEMP_DIR,
           LOADCHANGEMODULE = LOADCHANGEMODULE)

if OUT_OF_SAMPLE:
    run_empire(name = name, 
               tab_file_path = tab_file_path,
               result_file_path = result_file_path,
               scenariogeneration = scenariogeneration,
               scenario_data_path = scenario_data_path,
               solver = solver,
               temp_dir = temp_dir, 
               FirstHoursOfRegSeason = FirstHoursOfRegSeason, 
               FirstHoursOfPeakSeason = FirstHoursOfPeakSeason, 
               lengthRegSeason = lengthRegSeason,
               lengthPeakSeason = lengthPeakSeason,
               Period = Period, 
               Operationalhour = Operationalhour,
               Scenario = ScenarioOOS,
               Season = Season,
               HoursOfSeason = HoursOfSeason,
               discountrate = discountrate, 
               WACC = WACC, 
               LeapYearsInvestment = LeapYearsInvestment,
               HEATMODULE = HEATMODULE,
               DRMODULE = DRMODULE, 
               IAMC_PRINT = IAMC_PRINT, 
               WRITE_LP = WRITE_LP, 
               PICKLE_INSTANCE = PICKLE_INSTANCE, 
               EMISSION_CAP = EMISSION_CAP,
               OUT_OF_SAMPLE = OUT_OF_SAMPLE,
               sample_file_path = sample_file_path,
               USE_TEMP_DIR = USE_TEMP_DIR,
               LOADCHANGEMODULE = LOADCHANGEMODULE)
