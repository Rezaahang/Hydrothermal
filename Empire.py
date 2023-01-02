from __future__ import division
from pyomo.environ import *
from pyomo.common.tempfiles import TempfileManager
import csv
import sys
import cloudpickle
import time
import os

def run_empire(name, tab_file_path, result_file_path, scenariogeneration, scenario_data_path,
               solver, temp_dir, FirstHoursOfRegSeason, FirstHoursOfPeakSeason, lengthRegSeason,
               lengthPeakSeason, Period, Operationalhour, Scenario, Season, HoursOfSeason,
               discountrate, WACC, LeapYearsInvestment, HEATMODULE, DRMODULE,
               IAMC_PRINT, WRITE_LP, PICKLE_INSTANCE, EMISSION_CAP,
               OUT_OF_SAMPLE, sample_file_path, USE_TEMP_DIR, LOADCHANGEMODULE):

    if USE_TEMP_DIR:
        TempfileManager.tempdir = temp_dir

    if not os.path.exists(result_file_path):
        os.makedirs(result_file_path)

    model = AbstractModel()

    ###########
    ##SOLVERS##
    ###########

    if solver == "CPLEX":
        print("Solver: CPLEX")
    elif solver == "Xpress":
        print("Solver: Xpress")
    elif solver == "Gurobi":
        print("Solver: Gurobi")
    else:
        sys.exit("ERROR! Invalid solver! Options: CPLEX, Xpress, Gurobi")

    ##########
    ##MODULE##
    ##########

    if WRITE_LP:
        print("Will write LP-file...")

    if PICKLE_INSTANCE:
        print("Will pickle instance...")

    if EMISSION_CAP:
        print("Absolute emission cap in each scenario...")
    else:
        print("No absolute emission cap...")
    
    ########
    ##SETS##
    ########

    #Define the sets

    print("Declaring sets...")

    #Supply technology sets
    model.Generator = Set(ordered=True) #g
    model.Technology = Set(ordered=True) #t
    model.Storage =  Set() #b

    #Temporal sets
    model.Period = Set(ordered=True) #max period
    model.PeriodActive = Set(ordered=True, initialize=Period) #i
    model.Operationalhour = Set(ordered=True, initialize=Operationalhour) #h
    model.Season = Set(ordered=True, initialize=Season) #s

    #Spatial sets
    model.Node = Set(ordered=True) #n
    model.DirectionalLink = Set(dimen=2, within=model.Node*model.Node, ordered=True) #a
    model.TransmissionType = Set(ordered=True)

    #Stochastic sets
    model.Scenario = Set(ordered=True, initialize=Scenario) #w

    #Subsets
    model.GeneratorsOfTechnology=Set(dimen=2) #(t,g) for all t in T, g in G_t
    model.GeneratorsOfNode = Set(dimen=2) #(n,g) for all n in N, g in G_n
    model.TransmissionTypeOfDirectionalLink = Set(dimen=3) #(n1,n2,t) for all (n1,n2) in L, t in T
    model.ThermalGenerators = Set(within=model.Generator) #g_ramp
    model.RegHydroGenerator = Set(within=model.Generator) #g_reghyd
    model.HydroGenerator = Set(within=model.Generator) #g_hyd
    model.StoragesOfNode = Set(dimen=2) #(n,b) for all n in N, b in B_n
    model.DependentStorage = Set() #b_dagger
    model.HoursOfSeason = Set(dimen=2, ordered=True, initialize=HoursOfSeason) #(s,h) for all s in S, h in H_s
    model.FirstHoursOfRegSeason = Set(within=model.Operationalhour, ordered=True, initialize=FirstHoursOfRegSeason)
    model.FirstHoursOfPeakSeason = Set(within=model.Operationalhour, ordered=True, initialize=FirstHoursOfPeakSeason)

    if HEATMODULE:
        #Sets with converters and separated TR and EL generators and storages
        model.Converter = Set() #r
        model.ConverterOfNode = Set(dimen=2) #(n,r) for all n in N, r in R_n
        model.GeneratorCHP = Set(ordered=True)
        model.GeneratorTR = Set(ordered=True) # G_TR
        model.StorageTR = Set(ordered=True) # B_TR
        model.DependentStorageTR = Set()
        model.ThermalGeneratorsHeat = Set()
        model.TechnologyHeat = Set()
        model.StoragesOfNodeHeat = Set(dimen=2)
        model.GeneratorsOfNodeHeat = Set(dimen=2)
        model.GeneratorsOfTechnologyHeat = Set(dimen=2)

        #Sets with representative neighbourhoods
        model.Neighbourhood = Set()
        model.NeighbourhoodOfNode = Set(dimen=2)

    if DRMODULE:
        #Sub-set of storage related to DR
        model.StorageDR = Set(ordered=True) #B_DR
        model.DependentStorageDR = Set()
        model.StoragesOfNodeDR = Set(dimen=2) #(n,b) for all n in N, b in B_DR
        model.CostPieceDR = Set(ordered=True)
        model.CostPiecesOfStorageDR = Set(dimen=2) #(b,p) for all b in B_DR, p in P

    print("Reading sets...")

    #Load the data

    data = DataPortal()
    data.load(filename=tab_file_path + "/" + 'Sets_Generator.tab',format="set", set=model.Generator)
    data.load(filename=tab_file_path + "/" + 'Sets_ThermalGenerators.tab',format="set", set=model.ThermalGenerators)
    data.load(filename=tab_file_path + "/" + 'Sets_HydroGenerator.tab',format="set", set=model.HydroGenerator)
    data.load(filename=tab_file_path + "/" + 'Sets_HydroGeneratorWithReservoir.tab',format="set", set=model.RegHydroGenerator)
    data.load(filename=tab_file_path + "/" + 'Sets_Storage.tab',format="set", set=model.Storage)
    data.load(filename=tab_file_path + "/" + 'Sets_DependentStorage.tab',format="set", set=model.DependentStorage)
    data.load(filename=tab_file_path + "/" + 'Sets_Technology.tab',format="set", set=model.Technology)
    data.load(filename=tab_file_path + "/" + 'Sets_Node.tab',format="set", set=model.Node)
    data.load(filename=tab_file_path + "/" + 'Sets_Horizon.tab',format="set", set=model.Period)
    data.load(filename=tab_file_path + "/" + 'Sets_DirectionalLines.tab',format="set", set=model.DirectionalLink)
    data.load(filename=tab_file_path + "/" + 'Sets_LineType.tab',format="set", set=model.TransmissionType)
    data.load(filename=tab_file_path + "/" + 'Sets_LineTypeOfDirectionalLines.tab',format="set", set=model.TransmissionTypeOfDirectionalLink)
    data.load(filename=tab_file_path + "/" + 'Sets_GeneratorsOfTechnology.tab',format="set", set=model.GeneratorsOfTechnology)
    data.load(filename=tab_file_path + "/" + 'Sets_GeneratorsOfNode.tab',format="set", set=model.GeneratorsOfNode)
    data.load(filename=tab_file_path + "/" + 'Sets_StorageOfNodes.tab',format="set", set=model.StoragesOfNode)

    if HEATMODULE:
        #Load the heat module set data
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_ElectrToHeatConverter.tab',format="set", set=model.Converter)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_ConverterOfNodes.tab',format="set", set=model.ConverterOfNode)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_GeneratorHeatAndElectricity.tab',format="set", set=model.GeneratorCHP)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_GeneratorHeat.tab',format="set", set=model.GeneratorTR)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_StorageHeat.tab',format="set", set=model.StorageTR)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_DependentStorageHeat.tab',format="set", set=model.DependentStorageTR)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_ThermalGenerators.tab',format="set", set=model.ThermalGeneratorsHeat)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_TechnologyHeat.tab',format="set", set=model.TechnologyHeat)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_StorageOfNodes.tab',format="set", set=model.StoragesOfNodeHeat)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_GeneratorsOfNode.tab',format="set", set=model.GeneratorsOfNodeHeat)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_GeneratorsOfTechnology.tab',format="set", set=model.GeneratorsOfTechnologyHeat)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_Neighbourhood.tab',format="set", set=model.Neighbourhood)
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleSets_NeighbourhoodOfNode.tab',format="set", set=model.NeighbourhoodOfNode)

    if DRMODULE:
        #Sub-set of storage related to DR
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleSets_StorageDemandResponse.tab',format="set", set=model.StorageDR)
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleSets_DependentStorage.tab',format="set", set=model.DependentStorageDR)
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleSets_CostPiece.tab',format="set", set=model.CostPieceDR)
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleSets_StorageOfNodes.tab',format="set", set=model.StoragesOfNodeDR)
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleSets_CostPiecesOfStorageDR.tab',format="set", set=model.CostPiecesOfStorageDR)

    print("Constructing sub sets...")

    #Build arc subsets

    def NodesLinked_init(model, node):
        retval = []
        for (i,j) in model.DirectionalLink:
            if j == node:
                retval.append(i)
        return retval
    model.NodesLinked = Set(model.Node, initialize=NodesLinked_init)

    def BidirectionalArc_init(model):
        retval = []
        for (i,j) in model.DirectionalLink:
            if i != j and (not (j,i) in retval):
                retval.append((i,j))
        return retval
    model.BidirectionalArc = Set(dimen=2, initialize=BidirectionalArc_init, ordered=True) #l

    if HEATMODULE:
        def GeneratorEL_init(model):
            retval = []
            for g in model.Generator:
                retval.append(g)
            return retval
        model.GeneratorEL = Set(within=model.Generator, initialize=GeneratorEL_init) # G_EL

        def StorageEL_init(model):
            retval = []
            for g in model.Storage:
                retval.append(g)
            return retval
        model.StorageEL = Set(within=model.Storage, initialize=StorageEL_init) # B_EL

        def prepSetsHeatModule_rule(model):
            for g in model.GeneratorTR:
                model.Generator.add(g)
            for g in model.GeneratorCHP:
                model.GeneratorEL.add(g)
            for g in model.ThermalGeneratorsHeat:
                model.ThermalGenerators.add(g)
            for b in model.StorageTR:
                model.Storage.add(b)
            for b in model.DependentStorageTR:
                model.DependentStorage.add(b)
            for t in model.TechnologyHeat:
                model.Technology.add(t)
            for nb in model.StoragesOfNodeHeat:
                model.StoragesOfNode.add(nb)
            for ng in model.GeneratorsOfNodeHeat:
                model.GeneratorsOfNode.add(ng)
            for tg in model.GeneratorsOfTechnologyHeat:
                model.GeneratorsOfTechnology.add(tg)
        model.build_SetsHeatModule = BuildAction(rule=prepSetsHeatModule_rule)

    if DRMODULE:
        def prepSetsDRModule_rule(model):
            for b in model.StorageDR:
                model.Storage.add(b)
                if HEATMODULE:
                    model.StorageEL.add(b)
            for b in model.DependentStorageDR:
                model.DependentStorage.add(b)
            for nb in model.StoragesOfNodeDR:
                model.StoragesOfNode.add(nb)
        model.build_SetsDRModule = BuildAction(rule=prepSetsDRModule_rule)

    ##############
    ##PARAMETERS##
    ##############

    #Define the parameters

    print("Declaring parameters...")

    #Scaling

    model.discountrate = Param(initialize=discountrate) 
    model.WACC = Param(initialize=WACC) 
    model.LeapYearsInvestment = Param(initialize=LeapYearsInvestment)
    model.operationalDiscountrate = Param(mutable=True)
    model.sceProbab = Param(model.Scenario, mutable=True)
    model.seasScale = Param(model.Season, initialize=1.0, mutable=True)
    model.lengthRegSeason = Param(initialize=lengthRegSeason) 
    model.lengthPeakSeason = Param(initialize=lengthPeakSeason) 

    #Cost

    model.genCapitalCost = Param(model.Generator, model.Period, default=0, mutable=True)
    model.transmissionTypeCapitalCost = Param(model.TransmissionType, model.Period, default=0, mutable=True)
    model.storPWCapitalCost = Param(model.Storage, model.Period, default=0, mutable=True)
    model.storENCapitalCost = Param(model.Storage, model.Period, default=0, mutable=True)
    model.genFixedOMCost = Param(model.Generator, model.Period, default=0, mutable=True)
    model.transmissionTypeFixedOMCost = Param(model.TransmissionType, model.Period, default=0, mutable=True)
    model.storPWFixedOMCost = Param(model.Storage, model.Period, default=0, mutable=True)
    model.storENFixedOMCost = Param(model.Storage, model.Period, default=0, mutable=True)
    model.genInvCost = Param(model.Generator, model.Period, default=9000000, mutable=True)
    model.transmissionInvCost = Param(model.BidirectionalArc, model.Period, default=3000000, mutable=True)
    model.storPWInvCost = Param(model.Storage, model.Period, default=1000000, mutable=True)
    model.storENInvCost = Param(model.Storage, model.Period, default=800000, mutable=True)
    model.transmissionLength = Param(model.BidirectionalArc, default=0, mutable=True)
    model.genVariableOMCost = Param(model.Generator, default=0.0, mutable=True)
    model.genFuelCost = Param(model.Generator, model.Period, default=0.0, mutable=True)
    model.genMargCost = Param(model.Generator, model.Period, default=600, mutable=True)
    model.genCO2TypeFactor = Param(model.Generator, default=0.0, mutable=True)
    model.nodeLostLoadCost = Param(model.Node, model.Period, default=22000.0)
    model.CO2price = Param(model.Period, default=0.0, mutable=True)
    model.CCSCostTSFix = Param(initialize=1149873.72) #NB! Hard-coded
    model.CCSCostTSVariable = Param(model.Period, default=0.0, mutable=True)
    model.CCSRemFrac = Param(initialize=0.9)

    #Node dependent technology limitations

    model.genRefInitCap = Param(model.GeneratorsOfNode, default=0.0, mutable=True)
    model.genScaleInitCap = Param(model.Generator, model.Period, default=0.0, mutable=True)
    model.genInitCap = Param(model.GeneratorsOfNode, model.Period, default=0.0, mutable=True)
    model.transmissionInitCap = Param(model.BidirectionalArc, model.Period, default=0.0, mutable=True)
    model.storPWInitCap = Param(model.StoragesOfNode, model.Period, default=0.0, mutable=True)
    model.storENInitCap = Param(model.StoragesOfNode, model.Period, default=0.0, mutable=True)
    model.genMaxBuiltCap = Param(model.Node, model.Technology, model.Period, default=500000.0, mutable=True)
    model.transmissionMaxBuiltCap = Param(model.BidirectionalArc, model.Period, default=20000.0, mutable=True)
    model.storPWMaxBuiltCap = Param(model.StoragesOfNode, model.Period, default=500000.0, mutable=True)
    model.storENMaxBuiltCap = Param(model.StoragesOfNode, model.Period, default=500000.0, mutable=True)
    model.genMaxInstalledCapRaw = Param(model.Node, model.Technology, default=0.0, mutable=True)
    model.genMaxInstalledCap = Param(model.Node, model.Technology, model.Period, default=0.0, mutable=True)
    model.transmissionMaxInstalledCapRaw = Param(model.BidirectionalArc, model.Period, default=0.0)
    model.transmissionMaxInstalledCap = Param(model.BidirectionalArc, model.Period, default=0.0, mutable=True)
    model.storPWMaxInstalledCap = Param(model.StoragesOfNode, model.Period, default=0.0, mutable=True)
    model.storPWMaxInstalledCapRaw = Param(model.StoragesOfNode, default=0.0, mutable=True)
    model.storENMaxInstalledCap = Param(model.StoragesOfNode, model.Period, default=0.0, mutable=True)
    model.storENMaxInstalledCapRaw = Param(model.StoragesOfNode, default=0.0, mutable=True)

    #Type dependent technology limitations

    model.genLifetime = Param(model.Generator, default=0.0, mutable=True)
    model.transmissionLifetime = Param(model.BidirectionalArc, default=40.0, mutable=True)
    model.storageLifetime = Param(model.Storage, default=0.0, mutable=True)
    model.genEfficiency = Param(model.Generator, model.Period, default=1.0, mutable=True)
    model.lineEfficiency = Param(model.DirectionalLink, default=0.97, mutable=True)
    model.storageChargeEff = Param(model.Storage, default=1.0, mutable=True)
    model.storageDischargeEff = Param(model.Storage, default=1.0, mutable=True)
    model.storageBleedEff = Param(model.Storage, default=1.0, mutable=True)
    model.genRampUpCap = Param(model.ThermalGenerators, default=0.0, mutable=True)
    model.storageDiscToCharRatio = Param(model.Storage, default=1.0, mutable=True) #NB! Hard-coded
    model.storagePowToEnergy = Param(model.DependentStorage, default=1.0, mutable=True)

    #Stochastic input

    model.sloadRaw = Param(model.Node, model.Operationalhour, model.Scenario, model.Period, default=0.0, mutable=True)
    model.sloadAnnualDemand = Param(model.Node, model.Period, default=0.0, mutable=True)
    model.sload = Param(model.Node, model.Operationalhour, model.Period, model.Scenario, default=0.0, mutable=True)
    model.genCapAvailTypeRaw = Param(model.Generator, default=1.0, mutable=True)
    model.genCapAvailStochRaw = Param(model.GeneratorsOfNode, model.Operationalhour, model.Scenario, model.Period, default=0.0, mutable=True)
    model.genCapAvail = Param(model.GeneratorsOfNode, model.Operationalhour, model.Scenario, model.Period, default=0.0, mutable=True)
    model.maxRegHydroGenRaw = Param(model.Node, model.Period, model.HoursOfSeason, model.Scenario, default=0.0, mutable=True)
    model.maxRegHydroGen = Param(model.Node, model.Period, model.Season, model.Scenario, default=0.0, mutable=True)
    model.maxHydroNode = Param(model.Node, default=0.0, mutable=True)
    model.storOperationalInit = Param(model.Storage, default=0.0, mutable=True) #Percentage of installed energy capacity initially

    if EMISSION_CAP:
        	model.CO2cap = Param(model.Period, default=5000.0, mutable=True)
    
    if LOADCHANGEMODULE:
        model.sloadMod = Param(model.Node, model.Operationalhour, model.Scenario, model.Period, default=0.0, mutable=True)
        if HEATMODULE:
            model.sloadModTR = Param(model.Node, model.Operationalhour, model.Scenario, model.Period, default=0.0, mutable=True)
    
    #Heat module input

    if HEATMODULE:
        #Declare heat module parameters
        model.ConverterCapitalCost = Param(model.Converter, model.Period, default=0)
        model.ConverterFixedOMCost = Param(model.Converter, model.Period, default=0)
        model.ConverterInvCost = Param(model.Converter, model.Period, mutable=True)
        model.ConverterLifetime = Param(model.Converter, default=0)
        model.ConverterEff = Param(model.Converter, initialize=1.0, mutable=True)
        model.ConverterInitCap = Param(model.ConverterOfNode, model.Period, default=0)
        model.ConverterMaxBuiltCap = Param(model.ConverterOfNode, model.Period, default=50000)
        model.ConverterMaxInstalledCapRaw = Param(model.ConverterOfNode, default=200000)
        model.ConverterMaxInstalledCap = Param(model.ConverterOfNode, model.Period, default=0, mutable=True)

        model.neighCapitalCost = Param(model.Neighbourhood, model.Period, default=0)
        model.neighFixedOMCost = Param(model.Neighbourhood, model.Period, default=0)
        model.neighInvCost = Param(model.Neighbourhood, model.Period, mutable=True)
        model.neighLifetime = Param(model.Neighbourhood, default=60)
        model.neighConverterEff = Param(model.NeighbourhoodOfNode, model.Operationalhour, model.Scenario, default=1.0, mutable=True)
        model.neighInitCap = Param(model.NeighbourhoodOfNode, model.Period, default=0)
        model.neighMaxBuiltCap = Param(model.NeighbourhoodOfNode, model.Period, default=50000)
        model.neighMaxInstalledCapRaw = Param(model.NeighbourhoodOfNode, default=200000)
        model.neighMaxInstalledCap = Param(model.NeighbourhoodOfNode, model.Period, default=200000, mutable=True)
        model.neighCO2quota = Param(model.Neighbourhood, default=0)

        model.neighGenElectricAvailStoch = Param(model.NeighbourhoodOfNode, model.Operationalhour, model.Scenario, default=0.0, mutable=True)
        model.neighGenHeatAvailStoch = Param(model.NeighbourhoodOfNode, model.Operationalhour, model.Scenario, default=0.0, mutable=True)
        model.neighConvAvailStoch = Param(model.NeighbourhoodOfNode, model.Operationalhour, model.Scenario, default=0.0, mutable=True)

        model.genCapitalCostHeat = Param(model.Generator, model.Period, default=0)
        model.genFixedOMCostHeat = Param(model.Generator, model.Period, default=0)
        model.genLifetimeHeat = Param(model.Generator, default=0.0)
        model.genVariableOMCostHeat = Param(model.Generator, default=0.0)
        model.genFuelCostHeat = Param(model.Generator, model.Period, default=0.0)
        model.genCO2TypeFactorHeat = Param(model.Generator, default=0.0)
        model.genEfficiencyHeat = Param(model.Generator, model.Period, default=1.0)
        model.genCHPEfficiencyRaw = Param(model.GeneratorEL, model.Period, default=0.0) 
        model.genCHPEfficiency = Param(model.GeneratorEL, model.Period, default=1.0, mutable=True) 
        model.genRampUpCapHeat = Param(model.ThermalGenerators, default=0.0)
        model.genCapAvailTypeRawHeat = Param(model.Generator, default=1.0, mutable=True)
        model.genRefInitCapHeat = Param(model.GeneratorsOfNode, default=0.0)
        model.genScaleInitCapHeat = Param(model.Generator, model.Period, default=0.0)
        model.genInitCapHeat = Param(model.GeneratorsOfNode, model.Period, default=0.0, mutable=True)
        model.genMaxBuiltCapHeat = Param(model.Node, model.Technology, model.Period, default=500000.0, mutable=True)
        model.genMaxInstalledCapRawHeat = Param(model.Node, model.Technology, default=0.0, mutable=True)

        model.storPWCapitalCostHeat = Param(model.Storage, model.Period, default=0)
        model.storENCapitalCostHeat = Param(model.Storage, model.Period, default=0)
        model.storPWFixedOMCostHeat = Param(model.Storage, model.Period, default=0)
        model.storENFixedOMCostHeat = Param(model.Storage, model.Period, default=0)
        model.storageLifetimeHeat = Param(model.Storage, default=0.0)
        model.storageChargeEffHeat = Param(model.Storage, default=1.0)
        model.storageDischargeEffHeat = Param(model.Storage, default=1.0)
        model.storageBleedEffHeat = Param(model.Storage, default=1.0)
        model.storPWInitCapHeat = Param(model.StoragesOfNode, model.Period, default=0.0)
        model.storENInitCapHeat = Param(model.StoragesOfNode, model.Period, default=0.0)
        model.storPWMaxBuiltCapHeat = Param(model.StoragesOfNode, model.Period, default=500000.0, mutable=True)
        model.storENMaxBuiltCapHeat = Param(model.StoragesOfNode, model.Period, default=500000.0, mutable=True)
        model.storPWMaxInstalledCapRawHeat = Param(model.StoragesOfNode, default=2000000.0, mutable=True)
        model.storENMaxInstalledCapRawHeat = Param(model.StoragesOfNode, default=2000000.0, mutable=True)
        model.storOperationalInitHeat = Param(model.Storage, default=0.0, mutable=True) #Percentage of installed energy capacity initially
        model.storagePowToEnergyTR = Param(model.DependentStorageTR, default=1.0, mutable=True)

        model.sloadRawTR = Param(model.Node, model.Operationalhour, model.Scenario, model.Period, default=0.0, mutable=True)
        model.sloadTR = Param(model.Node, model.Operationalhour, model.Period, model.Scenario, default=0.0, mutable=True)
        model.convAvail = Param(model.ConverterOfNode, model.Operationalhour, model.Scenario, model.Period, default=1.0, mutable=True)

        model.nodeLostLoadCostTR = Param(model.Node, model.Period, default=22000.0)
        model.sloadAnnualDemandTR = Param(model.Node, model.Period, default=0.0, mutable=True)
        model.ElectricHeatShare = Param(model.Node, default=0.0, mutable=True)

    if DRMODULE:
        #Declare DR module parameters
        model.DRdemand = Param(model.StoragesOfNodeDR, model.Operationalhour, model.Period, model.Scenario, default=0.0, mutable=True)
        model.DRmax = Param(model.StoragesOfNodeDR, model.Operationalhour, model.Period, model.Scenario, default=500000, mutable=True)
        model.storageDischargeAvail = Param(model.StoragesOfNodeDR, model.Operationalhour, model.Period, model.Scenario, default=1.0, mutable=True)
        model.storageChargeAvail = Param(model.StoragesOfNodeDR, model.Operationalhour, model.Period, model.Scenario, default=1.0, mutable=True)
        model.DRbaseline = Param(model.StoragesOfNode, model.Operationalhour, model.Period, model.Scenario, default=0.0, mutable=True)

        model.storMargPieceCostDR = Param(model.CostPiecesOfStorageDR, default=0.0, mutable=True)
        model.storMargPieceActivationDR = Param(model.CostPiecesOfStorageDR, default=1.0, mutable=True)
        model.storPWCapitalCostDR = Param(model.Storage, model.Period, default=0)
        model.storENCapitalCostDR = Param(model.Storage, model.Period, default=0)
        model.storPWFixedOMCostDR = Param(model.Storage, model.Period, default=0)
        model.storENFixedOMCostDR = Param(model.Storage, model.Period, default=0)
        model.storageLifetimeDR = Param(model.Storage, default=0.0)
        model.storageChargeEffDR = Param(model.Storage, default=1.0)
        model.storageDischargeEffDR = Param(model.Storage, default=1.0)
        model.storageBleedEffDR = Param(model.Storage, default=1.0)
        model.storPWInitCapDR = Param(model.StoragesOfNode, model.Period, default=0.0)
        model.storENInitCapDR = Param(model.StoragesOfNode, model.Period, default=0.0)
        model.storPWMaxBuiltCapDR = Param(model.StoragesOfNode, model.Period, default=500000.0, mutable=True)
        model.storENMaxBuiltCapDR = Param(model.StoragesOfNode, model.Period, default=500000.0, mutable=True)
        model.storPWMaxInstalledCapRawDR = Param(model.StoragesOfNode, default=0.0, mutable=True)
        model.storENMaxInstalledCapRawDR = Param(model.StoragesOfNode, default=0.0, mutable=True)
        model.storOperationalInitDR = Param(model.Storage, default=0.0, mutable=True) #Percentage of installed energy capacity initially
        model.storagePowToEnergyDR = Param(model.DependentStorageDR, default=1.0, mutable=True)

    #Load the parameters

    print("Reading parameters...")
    
    if scenariogeneration:
        scenariopath = tab_file_path
    else:
        if OUT_OF_SAMPLE:
            scenariopath = sample_file_path
        else:
            scenariopath = scenario_data_path

    data.load(filename=tab_file_path + "/" + 'Generator_CapitalCosts.tab', param=model.genCapitalCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_FixedOMCosts.tab', param=model.genFixedOMCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_VariableOMCosts.tab', param=model.genVariableOMCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_FuelCosts.tab', param=model.genFuelCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_CCSCostTSVariable.tab', param=model.CCSCostTSVariable, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_Efficiency.tab', param=model.genEfficiency, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_RefInitialCap.tab', param=model.genRefInitCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_ScaleFactorInitialCap.tab', param=model.genScaleInitCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_InitialCapacity.tab', param=model.genInitCap, format="table") #node_generator_intial_capacity.xlsx
    data.load(filename=tab_file_path + "/" + 'Generator_MaxBuiltCapacity.tab', param=model.genMaxBuiltCap, format="table")#?
    data.load(filename=tab_file_path + "/" + 'Generator_MaxInstalledCapacity.tab', param=model.genMaxInstalledCapRaw, format="table")#maximum_capacity_constraint_040317_high
    data.load(filename=tab_file_path + "/" + 'Generator_CO2Content.tab', param=model.genCO2TypeFactor, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_RampRate.tab', param=model.genRampUpCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_GeneratorTypeAvailability.tab', param=model.genCapAvailTypeRaw, format="table")
    data.load(filename=tab_file_path + "/" + 'Generator_Lifetime.tab', param=model.genLifetime, format="table") 

    data.load(filename=tab_file_path + "/" + 'Transmission_InitialCapacity.tab', param=model.transmissionInitCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Transmission_MaxBuiltCapacity.tab', param=model.transmissionMaxBuiltCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Transmission_MaxInstallCapacityRaw.tab', param=model.transmissionMaxInstalledCapRaw, format="table")
    data.load(filename=tab_file_path + "/" + 'Transmission_Length.tab', param=model.transmissionLength, format="table")
    data.load(filename=tab_file_path + "/" + 'Transmission_TypeCapitalCost.tab', param=model.transmissionTypeCapitalCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Transmission_TypeFixedOMCost.tab', param=model.transmissionTypeFixedOMCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Transmission_lineEfficiency.tab', param=model.lineEfficiency, format="table")
    data.load(filename=tab_file_path + "/" + 'Transmission_Lifetime.tab', param=model.transmissionLifetime, format="table")

    data.load(filename=tab_file_path + "/" + 'Storage_StorageBleedEfficiency.tab', param=model.storageBleedEff, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_StorageChargeEff.tab', param=model.storageChargeEff, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_StorageDischargeEff.tab', param=model.storageDischargeEff, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_StoragePowToEnergy.tab', param=model.storagePowToEnergy, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_EnergyCapitalCost.tab', param=model.storENCapitalCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_EnergyFixedOMCost.tab', param=model.storENFixedOMCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_EnergyInitialCapacity.tab', param=model.storENInitCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_EnergyMaxBuiltCapacity.tab', param=model.storENMaxBuiltCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_EnergyMaxInstalledCapacity.tab', param=model.storENMaxInstalledCapRaw, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_StorageInitialEnergyLevel.tab', param=model.storOperationalInit, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_PowerCapitalCost.tab', param=model.storPWCapitalCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_PowerFixedOMCost.tab', param=model.storPWFixedOMCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_InitialPowerCapacity.tab', param=model.storPWInitCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_PowerMaxBuiltCapacity.tab', param=model.storPWMaxBuiltCap, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_PowerMaxInstalledCapacity.tab', param=model.storPWMaxInstalledCapRaw, format="table")
    data.load(filename=tab_file_path + "/" + 'Storage_Lifetime.tab', param=model.storageLifetime, format="table")

    data.load(filename=tab_file_path + "/" + 'Node_NodeLostLoadCost.tab', param=model.nodeLostLoadCost, format="table")
    data.load(filename=tab_file_path + "/" + 'Node_ElectricAnnualDemand.tab', param=model.sloadAnnualDemand, format="table") 
    data.load(filename=tab_file_path + "/" + 'Node_HydroGenMaxAnnualProduction.tab', param=model.maxHydroNode, format="table") 

    data.load(filename=scenariopath + "/" + 'Stochastic_HydroGenMaxSeasonalProduction.tab', param=model.maxRegHydroGenRaw, format="table")
    data.load(filename=scenariopath + "/" + 'Stochastic_StochasticAvailability.tab', param=model.genCapAvailStochRaw, format="table") 
    data.load(filename=scenariopath + "/" + 'Stochastic_ElectricLoadRaw.tab', param=model.sloadRaw, format="table") 

    data.load(filename=tab_file_path + "/" + 'General_seasonScale.tab', param=model.seasScale, format="table") 

    if EMISSION_CAP:
        data.load(filename=tab_file_path + "/" + 'General_CO2Cap.tab', param=model.CO2cap, format="table")
    else:
        data.load(filename=tab_file_path + "/" + 'General_CO2Price.tab', param=model.CO2price, format="table")
    
    if LOADCHANGEMODULE:
        data.load(filename=scenariopath + "/" + 'LoadchangeModule/Stochastic_ElectricLoadMod.tab', param=model.sloadMod, format="table")
        if HEATMODULE:
            data.load(filename=scenariopath + "/" + 'LoadchangeModule/Stochastic_HeatLoadMod.tab', param=model.sloadModTR, format="table")
    
    if HEATMODULE:
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleConverter_CapitalCosts.tab', param=model.ConverterCapitalCost, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleConverter_FixedOMCosts.tab', param=model.ConverterFixedOMCost, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleConverter_Efficiency.tab', param=model.ConverterEff, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleConverter_InitialCapacity.tab', param=model.ConverterInitCap, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleConverter_MaxBuildCapacity.tab', param=model.ConverterMaxBuiltCap, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleConverter_MaxInstallCapacity.tab', param=model.ConverterMaxInstalledCapRaw, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleConverter_Lifetime.tab', param=model.ConverterLifetime, format="table")

        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_CapitalCosts.tab', param=model.neighCapitalCost, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_FixedOMCosts.tab', param=model.neighFixedOMCost, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_InitialCapacity.tab', param=model.neighInitCap, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_MaxBuildCapacity.tab', param=model.neighMaxBuiltCap, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_MaxInstallCapacity.tab', param=model.neighMaxInstalledCapRaw, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_Lifetime.tab', param=model.neighLifetime, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_ElectricAvailability.tab', param=model.neighGenElectricAvailStoch, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_HeatAvailability.tab', param=model.neighGenHeatAvailStoch, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_ConverterAvailability.tab', param=model.neighConvAvailStoch, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_ConverterEfficiency.tab', param=model.neighConverterEff, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNeighbourhood_CO2Replacement.tab', param=model.neighCO2quota, format="table")

        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_CapitalCosts.tab', param=model.genCapitalCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_FixedOMCosts.tab', param=model.genFixedOMCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_VariableOMCosts.tab', param=model.genVariableOMCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_FuelCosts.tab', param=model.genFuelCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_Efficiency.tab', param=model.genEfficiencyHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_RefInitialCap.tab', param=model.genRefInitCapHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_ScaleFactorInitialCap.tab', param=model.genScaleInitCapHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_InitialCapacity.tab', param=model.genInitCapHeat, format="table") #node_generator_intial_capacity.xlsx
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_MaxBuiltCapacity.tab', param=model.genMaxBuiltCapHeat, format="table")#?
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_MaxInstalledCapacity.tab', param=model.genMaxInstalledCapRawHeat, format="table")#maximum_capacity_constraint_040317_high
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_CO2Content.tab', param=model.genCO2TypeFactorHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_RampRate.tab', param=model.genRampUpCapHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_GeneratorTypeAvailability.tab', param=model.genCapAvailTypeRawHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_Lifetime.tab', param=model.genLifetimeHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleGenerator_CHPEfficiency.tab', param=model.genCHPEfficiencyRaw, format="table")

        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_StorageBleedEfficiency.tab', param=model.storageBleedEffHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_StorageChargeEff.tab', param=model.storageChargeEffHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_StorageDischargeEff.tab', param=model.storageDischargeEffHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_EnergyCapitalCost.tab', param=model.storENCapitalCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_EnergyFixedOMCost.tab', param=model.storENFixedOMCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_EnergyInitialCapacity.tab', param=model.storENInitCapHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_EnergyMaxBuiltCapacity.tab', param=model.storENMaxBuiltCapHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_EnergyMaxInstalledCapacity.tab', param=model.storENMaxInstalledCapRawHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_StorageInitialEnergyLevel.tab', param=model.storOperationalInitHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_PowerCapitalCost.tab', param=model.storPWCapitalCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_PowerFixedOMCost.tab', param=model.storPWFixedOMCostHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_InitialPowerCapacity.tab', param=model.storPWInitCapHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_PowerMaxBuiltCapacity.tab', param=model.storPWMaxBuiltCapHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_PowerMaxInstalledCapacity.tab', param=model.storPWMaxInstalledCapRawHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_Lifetime.tab', param=model.storageLifetimeHeat, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleStorage_StoragePowToEnergy.tab', param=model.storagePowToEnergyTR, format="table")

        data.load(filename=scenariopath + "/" + 'HeatModule/HeatModuleStochastic_HeatLoadRaw.tab', param=model.sloadRawTR, format="table") 
        data.load(filename=scenariopath + "/" + 'HeatModule/HeatModuleStochastic_ConverterAvail.tab', param=model.convAvail, format="table")
        
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNode_HeatAnnualDemand.tab', param=model.sloadAnnualDemandTR, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNode_NodeLostLoadCost.tab', param=model.nodeLostLoadCostTR, format="table")
        data.load(filename=tab_file_path + "/" + 'HeatModule/HeatModuleNode_ElectricHeatShare.tab', param=model.ElectricHeatShare, format="table")   

    if DRMODULE:
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStochastic_DemandResponseDemand.tab', param=model.DRdemand, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStochastic_DemandResponseMax.tab', param=model.DRmax, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStochastic_DischargeAvailability.tab', param=model.storageDischargeAvail, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStochastic_ChargeAvailability.tab', param=model.storageChargeAvail, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStochastic_Baseline.tab', param=model.DRbaseline, format="table")

        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_DRMarginalPieceCost.tab', param=model.storMargPieceCostDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_DRMarginalPieceActivation.tab', param=model.storMargPieceActivationDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_StorageBleedEfficiency.tab', param=model.storageBleedEffDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_StorageChargeEff.tab', param=model.storageChargeEffDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_StorageDischargeEff.tab', param=model.storageDischargeEffDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_StoragePowToEnergy.tab', param=model.storagePowToEnergyDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_EnergyCapitalCost.tab', param=model.storENCapitalCostDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_EnergyFixedOMCost.tab', param=model.storENFixedOMCostDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_EnergyInitialCapacity.tab', param=model.storENInitCapDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_EnergyMaxBuiltCapacity.tab', param=model.storENMaxBuiltCapDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_EnergyMaxInstalledCapacity.tab', param=model.storENMaxInstalledCapRawDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_StorageInitialEnergyLevel.tab', param=model.storOperationalInitDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_PowerCapitalCost.tab', param=model.storPWCapitalCostDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_PowerFixedOMCost.tab', param=model.storPWFixedOMCostDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_InitialPowerCapacity.tab', param=model.storPWInitCapDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_PowerMaxBuiltCapacity.tab', param=model.storPWMaxBuiltCapDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_PowerMaxInstalledCapacity.tab', param=model.storPWMaxInstalledCapRawDR, format="table")
        data.load(filename=tab_file_path + "/" + 'DRModule/DRModuleStorage_Lifetime.tab', param=model.storageLifetimeDR, format="table")

    print("Constructing parameter values...")

    if HEATMODULE:
        def prepParametersHeatModule_rule(model):
            for g in model.GeneratorTR:
                model.genVariableOMCost[g] = model.genVariableOMCostHeat[g]
                model.genRampUpCap[g] = model.genRampUpCapHeat[g]
                model.genCapAvailTypeRaw[g] = model.genCapAvailTypeRawHeat[g]
                model.genCO2TypeFactor[g] = model.genCO2TypeFactorHeat[g]
                model.genLifetime[g] = model.genLifetimeHeat[g]
                for n in model.Node:
                    if (n,g) in model.GeneratorsOfNode:
                        model.genRefInitCap[n,g] = model.genRefInitCapHeat[n,g]
                for i in model.Period:
                    model.genCapitalCost[g,i] = model.genCapitalCostHeat[g,i]
                    model.genFixedOMCost[g,i] = model.genFixedOMCostHeat[g,i]
                    model.genFuelCost[g,i] = model.genFuelCostHeat[g,i]
                    model.genEfficiency[g,i] = model.genEfficiencyHeat[g,i]
                    model.genScaleInitCap[g,i] = model.genScaleInitCapHeat[g,i]
            for t in model.TechnologyHeat:
                for n in model.Node:
                    model.genMaxInstalledCapRaw[n,t] = model.genMaxInstalledCapRawHeat[n,t]
                    for i in model.Period:
                        model.genMaxBuiltCap[n,t,i] = model.genMaxBuiltCapHeat[n,t,i]
            for b in model.StorageTR:
                model.storOperationalInit[b] = model.storOperationalInitHeat[b]
                model.storageChargeEff[b] = model.storageChargeEffHeat[b]
                model.storageDischargeEff[b] = model.storageDischargeEffHeat[b]
                model.storageBleedEff[b] = model.storageBleedEffHeat[b]
                model.storageLifetime[b] = model.storageLifetimeHeat[b]
                if b in model.DependentStorageTR:
                    model.storagePowToEnergy[b] = model.storagePowToEnergyTR[b]
                for i in model.Period:
                    model.storPWCapitalCost[b,i] = model.storPWCapitalCostHeat[b,i]
                    model.storENCapitalCost[b,i] = model.storENCapitalCostHeat[b,i]
                    model.storPWFixedOMCost[b,i] = model.storPWFixedOMCostHeat[b,i]
                    model.storENFixedOMCost[b,i] = model.storENFixedOMCostHeat[b,i]
                for n in model.Node:
                    if (n,b) in model.StoragesOfNode:
                        model.storPWMaxInstalledCapRaw[n,b] = model.storPWMaxInstalledCapRawHeat[n,b]
                        model.storENMaxInstalledCapRaw[n,b] = model.storENMaxInstalledCapRawHeat[n,b]
                        for i in model.Period:
                            model.storPWInitCap[n,b,i] = model.storPWInitCapHeat[n,b,i]
                            model.storPWMaxBuiltCap[n,b,i] = model.storPWMaxBuiltCapHeat[n,b,i]
                            model.storENInitCap[n,b,i] = model.storENInitCapHeat[n,b,i]
                            model.storENMaxBuiltCap[n,b,i] = model.storENMaxBuiltCapHeat[n,b,i]
        model.build_ParametersHeatModule = BuildAction(rule=prepParametersHeatModule_rule)

    if DRMODULE:
        def prepParametersDRModule_rule(model):
            for b in model.StorageDR:
                model.storOperationalInit[b] = model.storOperationalInitDR[b]
                model.storageChargeEff[b] = model.storageChargeEffDR[b]
                model.storageDischargeEff[b] = model.storageDischargeEffDR[b]
                model.storageBleedEff[b] = model.storageBleedEffDR[b]
                model.storageLifetime[b] = model.storageLifetimeDR[b]
                if b in model.DependentStorageDR:
                    model.storagePowToEnergy[b] = model.storagePowToEnergyDR[b]
                for i in model.Period:
                    model.storPWCapitalCost[b,i] = model.storPWCapitalCostDR[b,i]
                    model.storENCapitalCost[b,i] = model.storENCapitalCostDR[b,i]
                    model.storPWFixedOMCost[b,i] = model.storPWFixedOMCostDR[b,i]
                    model.storENFixedOMCost[b,i] = model.storENFixedOMCostDR[b,i]
                for n in model.Node:
                    if (n,b) in model.StoragesOfNode:
                        model.storPWMaxInstalledCapRaw[n,b] = model.storPWMaxInstalledCapRawDR[n,b]
                        model.storENMaxInstalledCapRaw[n,b] = model.storENMaxInstalledCapRawDR[n,b]
                        for i in model.Period:
                            model.storPWInitCap[n,b,i] = model.storPWInitCapDR[n,b,i]
                            model.storPWMaxBuiltCap[n,b,i] = model.storPWMaxBuiltCapDR[n,b,i]
                            model.storENInitCap[n,b,i] = model.storENInitCapDR[n,b,i]
                            model.storENMaxBuiltCap[n,b,i] = model.storENMaxBuiltCapDR[n,b,i]
        model.build_ParametersDRModule = BuildAction(rule=prepParametersDRModule_rule)
        """
        def DRdemandReduction_init(model, n, b, h, i, w):
            #Build demand reduction for flexible demand resource

            retval = []
            for hh in model.FirstHoursOfRegSeason:
                if h >= hh and h <= value(hh + model.lengthRegSeason - 1):
                    retval = value(model.DRdemand[n,b,hh + model.lengthRegSeason - 1,i,w]/model.lengthRegSeason)
            for hh in model.FirstHoursOfPeakSeason:
                if h >= hh and h <= value(hh + model.lengthPeakSeason - 1):
                    retval = value(model.DRdemand[n,b,hh + model.lengthPeakSeason - 1,i,w]/model.lengthPeakSeason)
            return retval

        model.DRdemandReduction = Param(model.StoragesOfNodeDR, model.Operationalhour, model.Period, model.Scenario, initialize=DRdemandReduction_init)
        """

    #instance = model.create_instance(data)
    #instance.DRdemandReduction.pprint()
    #import pdb; pdb.set_trace()

    def prepSceProbab_rule(model):
    	#Build an equiprobable probability distribution for scenarios

    	for sce in model.Scenario:
    		model.sceProbab[sce] = value(1/len(model.Scenario))

    model.build_SceProbab = BuildAction(rule=prepSceProbab_rule)

    def prepInvCost_rule(model):
    	#Build investment cost for generators, storages and transmission. Annual cost is calculated for the lifetime of the generator and discounted for a year.
    	#Then cost is discounted for the investment period (or the remaining lifetime). CCS generators has additional fixed costs depending on emissions. 

    	#Generator 
    	for g in model.Generator:
    		for i in model.PeriodActive:
    			costperyear=(model.WACC/(1-((1+model.WACC)**(-model.genLifetime[g]))))*model.genCapitalCost[g,i]+model.genFixedOMCost[g,i]
    			costperperiod=costperyear*1000*(1-(1+model.discountrate)**-(min(value((len(model.PeriodActive)-i+1)*LeapYearsInvestment), value(model.genLifetime[g]))))/(1-(1/(1+model.discountrate)))
    			if ('CCS',g) in model.GeneratorsOfTechnology:
    				costperperiod+=model.CCSCostTSFix*model.CCSRemFrac*model.genCO2TypeFactor[g]*(3.6/model.genEfficiency[g,i])
    			model.genInvCost[g,i]=costperperiod

    	#Storage
    	for b in model.Storage:
    		for i in model.PeriodActive:
    			costperyearPW=(model.WACC/(1-((1+model.WACC)**(-model.storageLifetime[b]))))*model.storPWCapitalCost[b,i]+model.storPWFixedOMCost[b,i]
    			costperperiodPW=costperyearPW*1000*(1-(1+model.discountrate)**-(min(value((len(model.PeriodActive)-i+1)*LeapYearsInvestment), value(model.storageLifetime[b]))))/(1-(1/(1+model.discountrate)))
    			model.storPWInvCost[b,i]=costperperiodPW
    			costperyearEN=(model.WACC/(1-((1+model.WACC)**(-model.storageLifetime[b]))))*model.storENCapitalCost[b,i]+model.storENFixedOMCost[b,i]
    			costperperiodEN=costperyearEN*1000*(1-(1+model.discountrate)**-(min(value((len(model.PeriodActive)-i+1)*LeapYearsInvestment), value(model.storageLifetime[b]))))/(1-(1/(1+model.discountrate)))
    			model.storENInvCost[b,i]=costperperiodEN

    	#Transmission
    	for (n1,n2) in model.BidirectionalArc:
    		for i in model.PeriodActive:
    			for t in model.TransmissionType:
    				if (n1,n2,t) in model.TransmissionTypeOfDirectionalLink:
    					costperyear=(model.WACC/(1-((1+model.WACC)**(1-model.transmissionLifetime[n1,n2]))))*model.transmissionLength[n1,n2]*model.transmissionTypeCapitalCost[t,i]+model.transmissionTypeFixedOMCost[t,i]
    					costperperiod=costperyear*(1-(1+model.discountrate)**-(min(value((len(model.PeriodActive)-i+1)*LeapYearsInvestment), value(model.transmissionLifetime[n1,n2]))))/(1-(1/(1+model.discountrate)))
    					model.transmissionInvCost[n1,n2,i]=costperperiod

    model.build_InvCost = BuildAction(rule=prepInvCost_rule)

    def prepOperationalCostGen_rule(model):
    	#Build generator short term marginal costs

    	for g in model.Generator:
    		for i in model.PeriodActive:
    			if ('CCS',g) in model.GeneratorsOfTechnology:
    				costperenergyunit=(3.6/model.genEfficiency[g,i])*(model.genFuelCost[g,i]+(1-model.CCSRemFrac)*model.genCO2TypeFactor[g]*model.CO2price[i])+ \
    				(3.6/model.genEfficiency[g,i])*(model.CCSRemFrac*model.genCO2TypeFactor[g]*model.CCSCostTSVariable[i])+ \
    				model.genVariableOMCost[g]
    			else:
    				costperenergyunit=(3.6/model.genEfficiency[g,i])*(model.genFuelCost[g,i]+model.genCO2TypeFactor[g]*model.CO2price[i])+ \
    				model.genVariableOMCost[g]
    			model.genMargCost[g,i]=costperenergyunit

    model.build_OperationalCostGen = BuildAction(rule=prepOperationalCostGen_rule)

    def prepInitialCapacityNodeGen_rule(model):
    	#Build initial capacity for generator type in node

    	for (n,g) in model.GeneratorsOfNode:
    		for i in model.PeriodActive:
    			if value(model.genInitCap[n,g,i]) == 0:
    				model.genInitCap[n,g,i] = model.genRefInitCap[n,g]*(1-model.genScaleInitCap[g,i])

    model.build_InitialCapacityNodeGen = BuildAction(rule=prepInitialCapacityNodeGen_rule)

    def prepInitialCapacityTransmission_rule(model):
    	#Build initial capacity for transmission lines to ensure initial capacity is the upper installation bound if infeasible

    	for (n1,n2) in model.BidirectionalArc:
    		for i in model.PeriodActive:
    			if value(model.transmissionMaxInstalledCapRaw[n1,n2,i]) <= value(model.transmissionInitCap[n1,n2,i]):
    				model.transmissionMaxInstalledCap[n1,n2,i] = model.transmissionInitCap[n1,n2,i]
    			else:
    				model.transmissionMaxInstalledCap[n1,n2,i] = model.transmissionMaxInstalledCapRaw[n1,n2,i]

    model.build_InitialCapacityTransmission = BuildAction(rule=prepInitialCapacityTransmission_rule)

    def prepOperationalDiscountrate_rule(model):
    	#Build operational discount rate

        model.operationalDiscountrate = sum((1+model.discountrate)**(-j) for j in list(range(0,value(model.LeapYearsInvestment))))

    model.build_operationalDiscountrate = BuildAction(rule=prepOperationalDiscountrate_rule)     

    def prepGenMaxInstalledCap_rule(model):
    	#Build resource limit (installed limit) for all periods. Avoid infeasibility if installed limit lower than initially installed cap.

        for t in model.Technology:
            for n in model.Node:
                for i in model.PeriodActive:
                    if value(model.genMaxInstalledCapRaw[n,t] <= sum(model.genInitCap[n,g,i] for g in model.Generator if (n,g) in model.GeneratorsOfNode and (t,g) in model.GeneratorsOfTechnology)):
                        model.genMaxInstalledCap[n,t,i]=sum(model.genInitCap[n,g,i] for g in model.Generator if (n,g) in model.GeneratorsOfNode and (t,g) in model.GeneratorsOfTechnology)
                    else:
                        model.genMaxInstalledCap[n,t,i]=model.genMaxInstalledCapRaw[n,t]
                        
    model.build_genMaxInstalledCap = BuildAction(rule=prepGenMaxInstalledCap_rule)

    def storENMaxInstalledCap_rule(model):
    	#Build installed limit (resource limit) for storEN

        for (n,b) in model.StoragesOfNode:
            for i in model.PeriodActive:
                model.storENMaxInstalledCap[n,b,i]=model.storENMaxInstalledCapRaw[n,b]

    model.build_storENMaxInstalledCap = BuildAction(rule=storENMaxInstalledCap_rule)

    def storPWMaxInstalledCap_rule(model):
    	#Build installed limit (resource limit) for storPW

        for (n,b) in model.StoragesOfNode:
            for i in model.PeriodActive:
                model.storPWMaxInstalledCap[n,b,i]=model.storPWMaxInstalledCapRaw[n,b]

    model.build_storPWMaxInstalledCap = BuildAction(rule=storPWMaxInstalledCap_rule)

    def prepRegHydro_rule(model):
    	#Build hydrolimits for all periods

        for n in model.Node:
            for s in model.Season:
                for i in model.PeriodActive:
                    for sce in model.Scenario:
                        model.maxRegHydroGen[n,i,s,sce]=sum(model.maxRegHydroGenRaw[n,i,s,h,sce] for h in model.Operationalhour if (s,h) in model.HoursOfSeason)

    model.build_maxRegHydroGen = BuildAction(rule=prepRegHydro_rule)

    def prepGenCapAvail_rule(model):
    	#Build generator availability for all periods

        for (n,g) in model.GeneratorsOfNode:
            for h in model.Operationalhour:
                for s in model.Scenario:
                    for i in model.PeriodActive:
                        if value(model.genCapAvailTypeRaw[g]) == 0:
                            model.genCapAvail[n,g,h,s,i]=model.genCapAvailStochRaw[n,g,h,s,i]
                        else:
                            model.genCapAvail[n,g,h,s,i]=model.genCapAvailTypeRaw[g]

    model.build_genCapAvail = BuildAction(rule=prepGenCapAvail_rule)

    def prepSload_rule(model):
    	#Build load profiles for all periods

        counter = 0
        f = open(result_file_path + '/AdjustedNegativeLoad_' + name + '.txt', 'w')
        for n in model.Node:
            for i in model.PeriodActive:
                noderawdemand = 0
                for (s,h) in model.HoursOfSeason:
                    if value(h) < value(FirstHoursOfRegSeason[-1] + model.lengthRegSeason):
                        for sce in model.Scenario:
                                noderawdemand += value(model.sceProbab[sce]*model.seasScale[s]*model.sloadRaw[n,h,sce,i])
                if value(model.sloadAnnualDemand[n,i]) < 1:
                    hourlyscale = 0
                else:
                    hourlyscale = value(model.sloadAnnualDemand[n,i]) / noderawdemand
                for h in model.Operationalhour:
                    for sce in model.Scenario:
                        model.sload[n, h, i, sce] = model.sloadRaw[n,h,sce,i]*hourlyscale
                        """
                        if DRMODULE:
                            model.sload[n,h,i,sce] = model.sload[n,h,i,sce] - sum(model.DRdemandReduction[n,b,h,i,sce] for b in model.StorageDR if (n,b) in model.StoragesOfNode)
                        """
                        if HEATMODULE:
                            model.sload[n,h,i,sce] = model.sload[n,h,i,sce] - model.ElectricHeatShare[n]*model.sloadRawTR[n,h,sce,i]
                        if LOADCHANGEMODULE:
                            model.sload[n,h,i,sce] = model.sload[n,h,i,sce] + model.sloadMod[n,h,sce,i]
                        if value(model.sload[n,h,i,sce]) < 0:
                            f.write('Adjusted electricity load: ' + str(value(model.sload[n,h,i,sce])) + ', 10 MW for hour ' + str(h) + ' and scenario ' + str(sce) + ' in ' + str(n) + "\n")
                            model.sload[n,h,i,sce] = 10
                            counter += 1

        f.write('Hours with too small raw electricity load: ' + str(counter))
        f.close()

    model.build_sload = BuildAction(rule=prepSload_rule)

    if HEATMODULE:

        def prepInvCostConverter_rule(model):
        	#Build investment cost for Converter-converters

            for r in model.Converter:
                for i in model.PeriodActive:
                    costperyear=(model.WACC/(1-((1+model.WACC)**(-model.ConverterLifetime[r]))))*model.ConverterCapitalCost[r,i]+model.ConverterFixedOMCost[r,i]
                    costperperiod=costperyear*1000*(1-(1+model.discountrate)**-(min(value((len(Period)-i+1)*model.LeapYearsInvestment), value(model.ConverterLifetime[r]))))/(1-(1/(1+model.discountrate)))
                    model.ConverterInvCost[r,i]=costperperiod

        model.build_InvCostConverter = BuildAction(rule=prepInvCostConverter_rule)

        def prepInvCostNeighbourhood_rule(model):
            #Build investment cost for neighbourhoods

            for z in model.Neighbourhood:
                for i in model.PeriodActive:
                    costperyear=(model.WACC/(1-((1+model.WACC)**(-model.neighLifetime[z]))))*model.neighCapitalCost[z,i]+model.neighFixedOMCost[z,i]
                    costperperiod=costperyear*1000*(1-(1+model.discountrate)**-(min(value((len(Period)-i+1)*model.LeapYearsInvestment), value(model.neighLifetime[z]))))/(1-(1/(1+model.discountrate)))
                    model.neighInvCost[z,i]=costperperiod

        model.build_InvCostNeighbourhood = BuildAction(rule=prepInvCostNeighbourhood_rule) 	

        def prepSloadTR_rule(model):
            #Build heat load profiles for all periods
            
            counter = 0
            f = open(result_file_path + '/AdjustedNegativeLoad_' + name + '.txt', 'a')
            f.write('')
            for n in model.Node:
                for i in model.PeriodActive:
                    noderawdemandTR = 0
                    for (s,h) in model.HoursOfSeason:
                        if value(h) < value(model.FirstHoursOfRegSeason[-1] + model.lengthRegSeason):
                            for sce in model.Scenario:
                                noderawdemandTR += value(model.sceProbab[sce]*model.seasScale[s]*model.sloadRawTR[n,h,sce,i])
                    hourlyscaleTR = model.sloadAnnualDemandTR[n,i].value / noderawdemandTR
                    for h in model.Operationalhour:
                        for sce in model.Scenario:
                            model.sloadTR[n,h,i,sce] = model.sloadRawTR[n,h,sce,i]*hourlyscaleTR
                            if LOADCHANGEMODULE:
                                model.sloadTR[n,h,i,sce] = model.sloadTR[n,h,i,sce] + model.sloadModTR[n,h,sce,i]
                            if value(model.sloadTR[n,h,i,sce]) < 0:
                                f.write('Adjusted heat load: ' + str(value(model.sloadTR[n,h,i,sce])) + ', 0 MW for hour ' + str(h) + ' and scenario ' + str(sce) + ' in ' + str(n) + "\n")
                                model.sloadTR[n,h,i,sce] = 0
                                counter += 1
            f.write('Hours with too small raw heat load: ' + str(counter))
            f.close()

        model.build_sloadTR = BuildAction(rule=prepSloadTR_rule)

        def prepCHP_rule(model):
        	#Build CHP coefficients for CHP generators

            for i in model.PeriodActive:
                for g in model.GeneratorEL:
                    if g in model.GeneratorTR:
                        model.genCHPEfficiency[g,i] = model.genCHPEfficiencyRaw[g,i]

        model.build_CHPeff = BuildAction(rule=prepCHP_rule)

        def ConverterMaxInstalledCap_rule(model):
        	#Build resource limit for electricity to heat converters

            for (n,r) in model.ConverterOfNode:
                for i in model.PeriodActive:
                    model.ConverterMaxInstalledCap[n,r,i]=model.ConverterMaxInstalledCapRaw[n,r]

        model.build_ConverterMaxInstalledCap = BuildAction(rule=ConverterMaxInstalledCap_rule)

        def NeighbourhoodMaxInstalledCap_rule(model):
        	#Build resource limit for electricity to heat converters

            for (n,z) in model.NeighbourhoodOfNode:
                for i in model.PeriodActive:
                    model.neighMaxInstalledCap[n,z,i]=model.neighMaxInstalledCapRaw[n,z]

        model.build_NeighbourhoodMaxInstalledCap = BuildAction(rule=NeighbourhoodMaxInstalledCap_rule)

    #instance = model.create_instance(data)
    #instance.storPWMaxInstalledCap.pprint()
    #import pdb; pdb.set_trace()

    print("Sets and parameters declared and read...")

    #############
    ##VARIABLES##
    #############

    print("Declaring variables...")

    if OUT_OF_SAMPLE:
        model.genInvCap = Param(model.GeneratorsOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.transmisionInvCap = Param(model.BidirectionalArc, model.PeriodActive, domain=NonNegativeReals)
        model.storPWInvCap = Param(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.storENInvCap = Param(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.genInstalledCap = Param(model.GeneratorsOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.transmisionInstalledCap = Param(model.BidirectionalArc, model.PeriodActive, domain=NonNegativeReals)
        model.storPWInstalledCap = Param(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.storENInstalledCap = Param(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        
        data.load(filename=result_file_path + "/" + 'genInvCap.tab', param=model.genInvCap, format="table")
        data.load(filename=result_file_path + "/" + 'transmisionInvCap.tab', param=model.transmisionInvCap, format="table")
        data.load(filename=result_file_path + "/" + 'storPWInvCap.tab', param=model.storPWInvCap, format="table")
        data.load(filename=result_file_path + "/" + 'storENInvCap.tab', param=model.storENInvCap, format="table")
        data.load(filename=result_file_path + "/" + 'genInstalledCap.tab', param=model.genInstalledCap, format="table")
        data.load(filename=result_file_path + "/" + 'transmisionInstalledCap.tab', param=model.transmisionInstalledCap, format="table")
        data.load(filename=result_file_path + "/" + 'storPWInstalledCap.tab', param=model.storPWInstalledCap, format="table")
        data.load(filename=result_file_path + "/" + 'storENInstalledCap.tab', param=model.storENInstalledCap, format="table")
        
        result_file_path = result_file_path + "out-of-sample"
        
        if not os.path.exists(result_file_path):
            os.makedirs(result_file_path)
    else:    
        model.genInvCap = Var(model.GeneratorsOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.transmisionInvCap = Var(model.BidirectionalArc, model.PeriodActive, domain=NonNegativeReals)
        model.storPWInvCap = Var(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.storENInvCap = Var(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.genInstalledCap = Var(model.GeneratorsOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.transmisionInstalledCap = Var(model.BidirectionalArc, model.PeriodActive, domain=NonNegativeReals)
        model.storPWInstalledCap = Var(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.storENInstalledCap = Var(model.StoragesOfNode, model.PeriodActive, domain=NonNegativeReals)
        
    model.genOperational = Var(model.GeneratorsOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
    model.storOperational = Var(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
    model.transmisionOperational = Var(model.DirectionalLink, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals) #flow
    model.storCharge = Var(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
    model.storDischarge = Var(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
    model.loadShed = Var(model.Node, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)    

    if HEATMODULE:   
        model.ConverterOperational = Var(model.ConverterOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
        model.ConverterInvCap = Var(model.ConverterOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.ConverterInstalledCap = Var(model.ConverterOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.neighElectricOperational =Var(model.NeighbourhoodOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
        model.neighHeatOperational =Var(model.NeighbourhoodOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
        model.neighConverterOperational =Var(model.NeighbourhoodOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)
        model.neighInvCap = Var(model.NeighbourhoodOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.neighInstalledCap = Var(model.NeighbourhoodOfNode, model.PeriodActive, domain=NonNegativeReals)
        model.loadShedTR = Var(model.Node, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)

    if DRMODULE:
        model.storMargCost = Var(model.StoragesOfNodeDR, model.Operationalhour, model.PeriodActive, model.Scenario, domain=NonNegativeReals)

    ###############
    ##EXPRESSIONS##
    ###############

    def multiplier_rule(model,period):
        coeff=1
        if period>1:
            coeff=pow(1.0+model.discountrate,(-LeapYearsInvestment*(int(period)-1)))
        return coeff
    model.discount_multiplier=Expression(model.PeriodActive, rule=multiplier_rule)

    def shed_component_rule(model,i):
        return sum(model.operationalDiscountrate*model.seasScale[s]*model.sceProbab[w]*model.nodeLostLoadCost[n,i]*model.loadShed[n,h,i,w] for n in model.Node for w in model.Scenario for (s,h) in model.HoursOfSeason)
    model.shedcomponent=Expression(model.PeriodActive,rule=shed_component_rule)

    def operational_cost_rule(model,i):
        if DRMODULE:
            return sum(model.operationalDiscountrate*model.seasScale[s]*model.sceProbab[w]*model.genMargCost[g,i]*model.genOperational[n,g,h,i,w] for (n,g) in model.GeneratorsOfNode for (s,h) in model.HoursOfSeason for w in model.Scenario) + \
            sum(model.operationalDiscountrate*model.seasScale[s]*model.sceProbab[w]*model.storMargCost[n,b,h,i,w] for (n,b) in model.StoragesOfNodeDR for (s,h) in model.HoursOfSeason for w in model.Scenario)
        else:
            return sum(model.operationalDiscountrate*model.seasScale[s]*model.sceProbab[w]*model.genMargCost[g,i]*model.genOperational[n,g,h,i,w] for (n,g) in model.GeneratorsOfNode for (s,h) in model.HoursOfSeason for w in model.Scenario)
    model.operationalcost=Expression(model.PeriodActive,rule=operational_cost_rule)

    if HEATMODULE:
        def shed_componentTR_rule(model,i):
            return sum(model.operationalDiscountrate*model.seasScale[s]*model.sceProbab[w]*(model.nodeLostLoadCost[n,i]*model.loadShed[n,h,i,w] + model.nodeLostLoadCostTR[n,i]*model.loadShedTR[n,h,i,w]) for n in model.Node for w in model.Scenario for (s,h) in model.HoursOfSeason)
        model.shedcomponentTR=Expression(model.PeriodActive,rule=shed_componentTR_rule)

    #############
    ##OBJECTIVE##
    #############

    if HEATMODULE:
        def Obj_ruleTR(model):
            return sum(model.discount_multiplier[i]*(sum(model.genInvCost[g,i]* model.genInvCap[n,g,i] for (n,g) in model.GeneratorsOfNode ) + \
                sum(model.transmissionInvCost[n1,n2,i]*model.transmisionInvCap[n1,n2,i] for (n1,n2) in model.BidirectionalArc ) + \
                sum((model.storPWInvCost[b,i]*model.storPWInvCap[n,b,i]+model.storENInvCost[b,i]*model.storENInvCap[n,b,i]) for (n,b) in model.StoragesOfNode ) + \
                sum(model.ConverterInvCost[r,i]*model.ConverterInvCap[n,r,i] for (n,r) in model.ConverterOfNode ) + \
                sum(model.neighInvCost[z,i]*model.neighInvCap[n,z,i] for (n,z) in model.NeighbourhoodOfNode) + \
                model.shedcomponent[i] + model.shedcomponentTR[i] + model.operationalcost[i]) for i in model.PeriodActive)
        model.Obj = Objective(rule=Obj_ruleTR, sense=minimize)
    else:
        def Obj_rule(model):
            return sum(model.discount_multiplier[i]*(sum(model.genInvCost[g,i]* model.genInvCap[n,g,i] for (n,g) in model.GeneratorsOfNode ) + \
                sum(model.transmissionInvCost[n1,n2,i]*model.transmisionInvCap[n1,n2,i] for (n1,n2) in model.BidirectionalArc ) + \
                sum((model.storPWInvCost[b,i]*model.storPWInvCap[n,b,i]+model.storENInvCost[b,i]*model.storENInvCap[n,b,i]) for (n,b) in model.StoragesOfNode ) + \
                model.shedcomponent[i] + model.operationalcost[i]) for i in model.PeriodActive)
        model.Obj = Objective(rule=Obj_rule, sense=minimize)

    ###############
    ##CONSTRAINTS##
    ###############

    if HEATMODULE:
        def FlowBalanceEL_rule(model, n, h, i, w):
            return sum(model.genCHPEfficiency[g,i]*model.genOperational[n,g,h,i,w] for g in model.GeneratorEL if (n,g) in model.GeneratorsOfNode) \
                + sum(model.neighElectricOperational[n,z,h,i,w]-model.neighConverterOperational[n,z,h,i,w] for z in model.Neighbourhood if (n,z) in model.NeighbourhoodOfNode) \
                + sum((model.storageDischargeEff[b]*model.storDischarge[n,b,h,i,w]-model.storCharge[n,b,h,i,w]) for b in model.StorageEL if (n,b) in model.StoragesOfNode) \
                + sum((model.lineEfficiency[link,n]*model.transmisionOperational[link,n,h,i,w] - model.transmisionOperational[n,link,h,i,w]) for link in model.NodesLinked[n]) \
                - sum(model.ConverterOperational[n,r,h,i,w] for r in model.Converter if (n,r) in model.ConverterOfNode) \
                - model.sload[n,h,i,w] + model.loadShed[n,h,i,w] \
                == 0
        model.FlowBalance = Constraint(model.Node, model.Operationalhour, model.PeriodActive, model.Scenario, rule=FlowBalanceEL_rule)
    else:
        def FlowBalance_rule(model, n, h, i, w):
            return sum(model.genOperational[n,g,h,i,w] for g in model.Generator if (n,g) in model.GeneratorsOfNode) \
                + sum((model.storageDischargeEff[b]*model.storDischarge[n,b,h,i,w]-model.storCharge[n,b,h,i,w]) for b in model.Storage if (n,b) in model.StoragesOfNode) \
                + sum((model.lineEfficiency[link,n]*model.transmisionOperational[link,n,h,i,w] - model.transmisionOperational[n,link,h,i,w]) for link in model.NodesLinked[n]) \
                - model.sload[n,h,i,w] + model.loadShed[n,h,i,w] \
                == 0
        model.FlowBalance = Constraint(model.Node, model.Operationalhour, model.PeriodActive, model.Scenario, rule=FlowBalance_rule)

    #################################################################

    if HEATMODULE:
        def FlowBalanceTR_rule(model, n, h, i, w):
            return sum(model.genOperational[n,g,h,i,w] for g in model.GeneratorTR if (n,g) in model.GeneratorsOfNode) \
                + sum(model.neighHeatOperational[n,z,h,i,w]+model.neighConverterEff[n,z,h,w]*model.neighConverterOperational[n,z,h,i,w] for z in model.Neighbourhood if (n,z) in model.NeighbourhoodOfNode) \
                + sum((model.storageDischargeEff[b]*model.storDischarge[n,b,h,i,w]-model.storCharge[n,b,h,i,w]) for b in model.StorageTR if (n,b) in model.StoragesOfNode) \
                + sum(model.ConverterEff[r]*model.convAvail[n,r,h,w,i]*model.ConverterOperational[n,r,h,i,w] for r in model.Converter if (n,r) in model.ConverterOfNode) \
                - model.sloadTR[n,h,i,w] + model.loadShedTR[n,h,i,w] \
                == 0
        model.FlowBalanceTR = Constraint(model.Node, model.Operationalhour, model.PeriodActive, model.Scenario, rule=FlowBalanceTR_rule)

    #################################################################

    if HEATMODULE:
        def ConverterConv_rule(model, n, r, h, i, w):
            return model.ConverterOperational[n,r,h,i,w] - model.ConverterInstalledCap[n,r,i] <= 0
        model.ConverterConv = Constraint(model.ConverterOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=ConverterConv_rule)

    #################################################################

    if HEATMODULE:
        def NeighbourhoodElecProd_rule(model, n, z, h, i, w):
            return model.neighElectricOperational[n,z,h,i,w] - model.neighGenElectricAvailStoch[n,z,h,w]*model.neighInstalledCap[n,z,i] <= 0
        model.NeighbourhoodElecProd = Constraint(model.NeighbourhoodOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=NeighbourhoodElecProd_rule)

    #################################################################

    if HEATMODULE:
        def NeighbourhoodHeatProd_rule(model, n, z, h, i, w):
            return model.neighHeatOperational[n,z,h,i,w] - model.neighGenHeatAvailStoch[n,z,h,w]*model.neighInstalledCap[n,z,i] <= 0
        model.NeighbourhoodHeatProd = Constraint(model.NeighbourhoodOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=NeighbourhoodHeatProd_rule)

    #################################################################

    if HEATMODULE:
        def NeighbourhoodConvProd_rule(model, n, z, h, i, w):
            return model.neighConverterOperational[n,z,h,i,w] - model.neighConvAvailStoch[n,z,h,w]*model.neighInstalledCap[n,z,i] <= 0
        model.NeighbourhoodConvProd = Constraint(model.NeighbourhoodOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=NeighbourhoodConvProd_rule)

    #################################################################

    def genMaxProd_rule(model, n, g, h, i, w):
            return model.genOperational[n,g,h,i,w] - model.genCapAvail[n,g,h,w,i]*model.genInstalledCap[n,g,i] <= 0
    model.maxGenProduction = Constraint(model.GeneratorsOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=genMaxProd_rule)

    #################################################################

    def ramping_rule(model, n, g, h, i, w):
        if h in model.FirstHoursOfRegSeason or h in model.FirstHoursOfPeakSeason:
            return Constraint.Skip
        else:
            if g in model.ThermalGenerators:
                return model.genOperational[n,g,h,i,w]-model.genOperational[n,g,(h-1),i,w] - model.genRampUpCap[g]*model.genInstalledCap[n,g,i] <= 0   #
            else:
                return Constraint.Skip
    model.ramping = Constraint(model.GeneratorsOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=ramping_rule)

    #################################################################
    
    if DRMODULE:
        def storage_energy_balance_DR_rule(model, n, b, h, i, w):
            if h in model.FirstHoursOfRegSeason or h in model.FirstHoursOfPeakSeason:
                return model.storOperationalInit[b]*model.storENInstalledCap[n,b,i] + model.storageChargeEff[b]*model.storCharge[n,b,h,i,w]-model.storDischarge[n,b,h,i,w]+model.DRbaseline[n,b,h,i,w]-model.storOperational[n,b,h,i,w] == 0   #
            else:
                return model.storageBleedEff[b]*model.storOperational[n,b,(h-1),i,w] + model.storageChargeEff[b]*model.storCharge[n,b,h,i,w]-model.storDischarge[n,b,h,i,w]+model.DRbaseline[n,b,h,i,w]-model.storOperational[n,b,h,i,w] == 0   #        
        model.storage_energy_balance = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_energy_balance_DR_rule)
    else:
        def storage_energy_balance_rule(model, n, b, h, i, w):
            if h in model.FirstHoursOfRegSeason or h in model.FirstHoursOfPeakSeason:
                return model.storOperationalInit[b]*model.storENInstalledCap[n,b,i] + model.storageChargeEff[b]*model.storCharge[n,b,h,i,w]-model.storDischarge[n,b,h,i,w]-model.storOperational[n,b,h,i,w] == 0   #
            else:
                return model.storageBleedEff[b]*model.storOperational[n,b,(h-1),i,w] + model.storageChargeEff[b]*model.storCharge[n,b,h,i,w]-model.storDischarge[n,b,h,i,w]-model.storOperational[n,b,h,i,w] == 0   #
        model.storage_energy_balance = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_energy_balance_rule)

    #################################################################

    if DRMODULE:
        def storage_seasonal_net_zero_balance_DR_rule(model, n, b, h, i, w):
            if h in model.FirstHoursOfRegSeason:
                if b not in model.StorageDR:
                    return model.storOperational[n,b,h+value(model.lengthRegSeason)-1,i,w] - model.storOperationalInit[b]*model.storENInstalledCap[n,b,i] == 0  #
                else:
                    return Constraint.Skip
            elif h in model.FirstHoursOfPeakSeason:
                if b not in model.StorageDR:
                    return model.storOperational[n,b,h+value(model.lengthPeakSeason)-1,i,w] - model.storOperationalInit[b]*model.storENInstalledCap[n,b,i] == 0  #
                else:
                    return Constraint.Skip
            elif b in model.StorageDR:
                return model.DRdemand[n,b,h,i,w] - model.storOperational[n,b,h,i,w] <= 0
            else:
                return Constraint.Skip
        model.storage_seasonal_net_zero_balance = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_seasonal_net_zero_balance_DR_rule)
    else:
        def storage_seasonal_net_zero_balance_rule(model, n, b, h, i, w):
            if h in model.FirstHoursOfRegSeason:
                return model.storOperational[n,b,h+value(model.lengthRegSeason)-1,i,w] - model.storOperationalInit[b]*model.storENInstalledCap[n,b,i] == 0  #
            elif h in model.FirstHoursOfPeakSeason:
                return model.storOperational[n,b,h+value(model.lengthPeakSeason)-1,i,w] - model.storOperationalInit[b]*model.storENInstalledCap[n,b,i] == 0  #
            else:
                return Constraint.Skip
        model.storage_seasonal_net_zero_balance = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_seasonal_net_zero_balance_rule)

    #################################################################
    
    if DRMODULE:
        def DR_upper_bound_rule(model, n, b, h, i, w):
            return model.storOperational[n,b,h,i,w] - model.DRmax[n,b,h,i,w] <= 0
        model.DR_upper_bound = Constraint(model.StoragesOfNodeDR, model.Operationalhour, model.PeriodActive, model.Scenario, rule=DR_upper_bound_rule)
        
    #################################################################

    def storage_operational_cap_rule(model, n, b, h, i, w):
        return model.storOperational[n,b,h,i,w] - model.storENInstalledCap[n,b,i]  <= 0   #
    model.storage_operational_cap = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_operational_cap_rule)

    #################################################################

    if DRMODULE:
        def storage_power_discharg_cap_rule(model, n, b, h, i, w):
            if b in model.StorageDR:
                return model.storDischarge[n,b,h,i,w] - model.storageDischargeAvail[n,b,h,i,w]*model.storPWInstalledCap[n,b,i] <= 0   #
            else:
                return model.storDischarge[n,b,h,i,w] - model.storageDiscToCharRatio[b]*model.storPWInstalledCap[n,b,i] <= 0   #
        model.storage_power_discharg_cap = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_power_discharg_cap_rule)
    else:
        def storage_power_discharg_cap_rule(model, n, b, h, i, w):
            return model.storDischarge[n,b,h,i,w] - model.storageDiscToCharRatio[b]*model.storPWInstalledCap[n,b,i] <= 0   #
        model.storage_power_discharg_cap = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_power_discharg_cap_rule)

    #################################################################

    if DRMODULE:
        def storage_power_charg_cap_rule(model, n, b, h, i, w):
            if b in model.StorageDR:
                return model.storCharge[n,b,h,i,w] - model.storageChargeAvail[n,b,h,i,w]*model.storPWInstalledCap[n,b,i] <= 0   #
            else:
                return model.storCharge[n,b,h,i,w] - model.storPWInstalledCap[n,b,i] <= 0   #
        model.storage_power_charg_cap = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_power_charg_cap_rule)
    else:
        def storage_power_charg_cap_rule(model, n, b, h, i, w):
            return model.storCharge[n,b,h,i,w] - model.storPWInstalledCap[n,b,i] <= 0   #
        model.storage_power_charg_cap = Constraint(model.StoragesOfNode, model.Operationalhour, model.PeriodActive, model.Scenario, rule=storage_power_charg_cap_rule)

    #################################################################

    if DRMODULE:
        def DR_cost_def_rule(model, b1, p, n, b2, h, i, w):
            if b1==b2:
                return sum(model.storMargPieceCostDR[b1,p]*(model.storDischarge[n,b2,h,i,w] + model.storCharge[n,b2,h,i,w] - model.storPWInstalledCap[n,b2,i]*(1 - model.storMargPieceActivationDR[b1,p])) for pp in model.CostPieceDR if pp <= p) - model.storMargCost[n,b2,h,i,w] <= 0
            else:
                return Constraint.Skip
        model.DR_cost_def = Constraint(model.CostPiecesOfStorageDR, model.StoragesOfNodeDR, model.Operationalhour, model.PeriodActive, model.Scenario, rule=DR_cost_def_rule)

    #################################################################

    def hydro_gen_limit_rule(model, n, g, s, i, w):
        if g in model.RegHydroGenerator:
            return sum(model.genOperational[n,g,h,i,w] for h in model.Operationalhour if (s,h) in model.HoursOfSeason) - model.maxRegHydroGen[n,i,s,w] <= 0
        else:
            return Constraint.Skip  #
    model.hydro_gen_limit = Constraint(model.GeneratorsOfNode, model.Season, model.PeriodActive, model.Scenario, rule=hydro_gen_limit_rule)

    #################################################################

    def hydro_node_limit_rule(model, n, i):
        return sum(model.genOperational[n,g,h,i,w]*model.seasScale[s]*model.sceProbab[w] for g in model.HydroGenerator if (n,g) in model.GeneratorsOfNode for (s,h) in model.HoursOfSeason for w in model.Scenario) - model.maxHydroNode[n] <= 0   #
    model.hydro_node_limit = Constraint(model.Node, model.PeriodActive, rule=hydro_node_limit_rule)


    #################################################################

    def transmission_cap_rule(model, n1, n2, h, i, w):
        if (n1,n2) in model.BidirectionalArc:
            return model.transmisionOperational[(n1,n2),h,i,w]  - model.transmisionInstalledCap[(n1,n2),i] <= 0
        elif (n2,n1) in model.BidirectionalArc:
            return model.transmisionOperational[(n1,n2),h,i,w]  - model.transmisionInstalledCap[(n2,n1),i] <= 0
    model.transmission_cap = Constraint(model.DirectionalLink, model.Operationalhour, model.PeriodActive, model.Scenario, rule=transmission_cap_rule)

    #################################################################

    if EMISSION_CAP:
        if HEATMODULE:
            def emission_cap_rule(model, i, w):
                return sum(model.seasScale[s]*model.genCO2TypeFactor[g]*(3.6/model.genEfficiency[g,i])*model.genOperational[n,g,h,i,w] for (n,g) in model.GeneratorsOfNode for (s,h) in model.HoursOfSeason)/1000000 \
                    + sum(model.neighCO2quota[z]*model.neighInstalledCap[n,z,i] for (n,z) in model.NeighbourhoodOfNode)/1000000 \
                    - model.CO2cap[i] <= 0   #
            model.emission_cap = Constraint(model.PeriodActive, model.Scenario, rule=emission_cap_rule)
        else:
            def emission_cap_rule(model, i, w):
                return sum(model.seasScale[s]*model.genCO2TypeFactor[g]*(3.6/model.genEfficiency[g,i])*model.genOperational[n,g,h,i,w] for (n,g) in model.GeneratorsOfNode for (s,h) in model.HoursOfSeason)/1000000 \
                    - model.CO2cap[i] <= 0   #
            model.emission_cap = Constraint(model.PeriodActive, model.Scenario, rule=emission_cap_rule)

    #################################################################
    
    ########################
    #INVESTMENT CONSTRAINTS#
    ########################
    
    if not OUT_OF_SAMPLE:
        #################################################################
        if HEATMODULE:
            def lifetime_rule_Converter(model, n, r, i):
                startPeriod=1
                if value(1+i-(model.ConverterLifetime[r]/model.LeapYearsInvestment))>startPeriod:
                    startPeriod=value(1+i-model.ConverterLifetime[r]/model.LeapYearsInvestment)
                return sum(model.ConverterInvCap[n,r,j]  for j in model.PeriodActive if j>=startPeriod and j<=i )- model.ConverterInstalledCap[n,r,i] + model.ConverterInitCap[n,r,i] == 0   #
            model.installedCapDefinitionConverter = Constraint(model.ConverterOfNode, model.PeriodActive, rule=lifetime_rule_Converter)
    
        #################################################################
    
        if HEATMODULE:
            def lifetime_rule_Neighbourhood(model, n, z, i):
                startPeriod=1
                if value(1+i-(model.neighLifetime[z]/model.LeapYearsInvestment))>startPeriod:
                    startPeriod=value(1+i-model.neighLifetime[z]/model.LeapYearsInvestment)
                return sum(model.neighInvCap[n,z,j]  for j in model.PeriodActive if j>=startPeriod and j<=i )- model.neighInstalledCap[n,z,i] + model.neighInitCap[n,z,i] == 0   #
            model.installedCapDefinitionNeighbourhood = Constraint(model.NeighbourhoodOfNode, model.PeriodActive, rule=lifetime_rule_Neighbourhood)
    
        #################################################################
    
        def lifetime_rule_gen(model, n, g, i):
            startPeriod=1
            if value(1+i-(model.genLifetime[g]/model.LeapYearsInvestment))>startPeriod:
                startPeriod=value(1+i-model.genLifetime[g]/model.LeapYearsInvestment)
            return sum(model.genInvCap[n,g,j]  for j in model.PeriodActive if j>=startPeriod and j<=i )- model.genInstalledCap[n,g,i] + model.genInitCap[n,g,i]== 0   #
        model.installedCapDefinitionGen = Constraint(model.GeneratorsOfNode, model.PeriodActive, rule=lifetime_rule_gen)
    
        #################################################################
    
        def lifetime_rule_storEN(model, n, b, i):
            startPeriod=1
            if value(1+i-model.storageLifetime[b]*(1/model.LeapYearsInvestment))>startPeriod:
                startPeriod=value(1+i-model.storageLifetime[b]/model.LeapYearsInvestment)
            return sum(model.storENInvCap[n,b,j]  for j in model.PeriodActive if j>=startPeriod and j<=i )- model.storENInstalledCap[n,b,i] + model.storENInitCap[n,b,i]== 0   #
        model.installedCapDefinitionStorEN = Constraint(model.StoragesOfNode, model.PeriodActive, rule=lifetime_rule_storEN)
    
        #################################################################
    
        def lifetime_rule_storPOW(model, n, b, i):
            startPeriod=1
            if value(1+i-model.storageLifetime[b]*(1/model.LeapYearsInvestment))>startPeriod:
                startPeriod=value(1+i-model.storageLifetime[b]/model.LeapYearsInvestment)
            return sum(model.storPWInvCap[n,b,j]  for j in model.PeriodActive if j>=startPeriod and j<=i )- model.storPWInstalledCap[n,b,i] + model.storPWInitCap[n,b,i]== 0   #
        model.installedCapDefinitionStorPOW = Constraint(model.StoragesOfNode, model.PeriodActive, rule=lifetime_rule_storPOW)
    
        #################################################################
    
        def lifetime_rule_trans(model, n1, n2, i):
            startPeriod=1
            if value(1+i-model.transmissionLifetime[n1,n2]*(1/model.LeapYearsInvestment))>startPeriod:
                startPeriod=value(1+i-model.transmissionLifetime[n1,n2]/model.LeapYearsInvestment)
            return sum(model.transmisionInvCap[n1,n2,j]  for j in model.PeriodActive if j>=startPeriod and j<=i )- model.transmisionInstalledCap[n1,n2,i] + model.transmissionInitCap[n1,n2,i] == 0   #
        model.installedCapDefinitionTrans = Constraint(model.BidirectionalArc, model.PeriodActive, rule=lifetime_rule_trans)
    
        #################################################################
    
        if HEATMODULE:
            def investment_Converter_cap_rule(model, n, r, i):
                return model.ConverterInvCap[n,r,i] - model.ConverterMaxBuiltCap[n,r,i] <= 0
            model.investment_Converter_cap = Constraint(model.ConverterOfNode, model.PeriodActive, rule=investment_Converter_cap_rule)
    
        #################################################################
    
        if HEATMODULE:
            def investment_Neighbourhood_cap_rule(model, n, z, i):
                return model.neighInvCap[n,z,i] - model.neighMaxBuiltCap[n,z,i] <= 0
            model.investment_Neighbourhood_cap = Constraint(model.NeighbourhoodOfNode, model.PeriodActive, rule=investment_Neighbourhood_cap_rule)
    
        #################################################################
    
        def investment_gen_cap_rule(model, t, n, i):
            return sum(model.genInvCap[n,g,i] for g in model.Generator if (n,g) in model.GeneratorsOfNode and (t,g) in model.GeneratorsOfTechnology) - model.genMaxBuiltCap[n,t,i] <= 0
        model.investment_gen_cap = Constraint(model.Technology, model.Node, model.PeriodActive, rule=investment_gen_cap_rule)
    
        #################################################################
    
        def investment_trans_cap_rule(model, n1, n2, i):
            return model.transmisionInvCap[n1,n2,i] - model.transmissionMaxBuiltCap[n1,n2,i] <= 0
        model.investment_trans_cap = Constraint(model.BidirectionalArc, model.PeriodActive, rule=investment_trans_cap_rule)
    
        #################################################################
    
        def investment_storage_power_cap_rule(model, n, b, i):
            return model.storPWInvCap[n,b,i] - model.storPWMaxBuiltCap[n,b,i] <= 0
        model.investment_storage_power_cap = Constraint(model.StoragesOfNode, model.PeriodActive, rule=investment_storage_power_cap_rule)
    
        #################################################################
    
        def investment_storage_energy_cap_rule(model, n, b, i):
            return model.storENInvCap[n,b,i] - model.storENMaxBuiltCap[n,b,i] <= 0
        model.investment_storage_energy_cap = Constraint(model.StoragesOfNode, model.PeriodActive, rule=investment_storage_energy_cap_rule)
    
        ################################################################
    
        if HEATMODULE:
            def installed_Converter_cap_rule(model, n, r, i):
                return model.ConverterInstalledCap[n,r,i] - model.ConverterMaxInstalledCap[n,r,i] <= 0
            model.installed_Converter_cap = Constraint(model.ConverterOfNode, model.PeriodActive, rule=installed_Converter_cap_rule)
    
        ################################################################
    
        if HEATMODULE:
            def installed_Neighbourhood_cap_rule(model, n, z, i):
                return model.neighInstalledCap[n,z,i] - model.neighMaxInstalledCap[n,z,i] <= 0
            model.installed_Neighbourhood_cap = Constraint(model.NeighbourhoodOfNode, model.PeriodActive, rule=installed_Neighbourhood_cap_rule)
    
        #################################################################
    
        def installed_gen_cap_rule(model, t, n, i):
            return sum(model.genInstalledCap[n,g,i] for g in model.Generator if (n,g) in model.GeneratorsOfNode and (t,g) in model.GeneratorsOfTechnology) - model.genMaxInstalledCap[n,t,i] <= 0
        model.installed_gen_cap = Constraint(model.Technology, model.Node, model.PeriodActive, rule=installed_gen_cap_rule)
    
        #################################################################
    
        def installed_trans_cap_rule(model, n1, n2, i):
            return model.transmisionInstalledCap[n1,n2,i] - model.transmissionMaxInstalledCap[n1,n2,i] <= 0
        model.installed_trans_cap = Constraint(model.BidirectionalArc, model.PeriodActive, rule=installed_trans_cap_rule)
    
        #################################################################
    
        def installed_storage_power_cap_rule(model, n, b, i):
            return model.storPWInstalledCap[n,b,i] - model.storPWMaxInstalledCap[n,b,i] <= 0
        model.installed_storage_power_cap = Constraint(model.StoragesOfNode, model.PeriodActive, rule=installed_storage_power_cap_rule)
    
        #################################################################
    
        def installed_storage_energy_cap_rule(model, n, b, i):
            return model.storENInstalledCap[n,b,i] - model.storENMaxInstalledCap[n,b,i] <= 0
        model.installed_storage_energy_cap = Constraint(model.StoragesOfNode, model.PeriodActive, rule=installed_storage_energy_cap_rule)
    
        #################################################################
    
        def power_energy_relate_rule(model, n, b, i):
            if b in model.DependentStorage:
                return model.storPWInstalledCap[n,b,i] - model.storagePowToEnergy[b]*model.storENInstalledCap[n,b,i] == 0   #
            else:
                return Constraint.Skip
        model.power_energy_relate = Constraint(model.StoragesOfNode, model.PeriodActive, rule=power_energy_relate_rule)
    
        #################################################################

    #######
    ##RUN##
    #######

    print("Objective and constraints read...")

    print("Building instance...")

    start = time.time()

    instance = model.create_instance(data) #, report_timing=True)
    instance.dual = Suffix(direction=Suffix.IMPORT) #Make sure the dual value is collected into solver results (if solver supplies dual information)

    end = time.time()
    print("Building instance took [sec]:")
    print(end - start)

    #import pdb; pdb.set_trace()
    #instance.CO2price.pprint()

    print("----------------------Problem Statistics---------------------")
    if HEATMODULE:
        print("Heat module activated")
    if DRMODULE:
        print("DR module activated")
    print("")
    print("Nodes: "+ str(len(instance.Node)))
    print("Lines: "+str(len(instance.BidirectionalArc)))
    print("")
    print("GeneratorTypes: "+str(len(instance.Generator)))
    if HEATMODULE:
        print("GeneratorEL: "+str(len(instance.GeneratorEL)))
        print("GeneratorTR: "+str(len(instance.GeneratorTR)))
    print("TotalGenerators: "+str(len(instance.GeneratorsOfNode)))
    print("StorageTypes: "+str(len(instance.Storage)))
    print("TotalStorages: "+str(len(instance.StoragesOfNode)))
    if HEATMODULE:
        print("ConverterConverters: "+str(len(instance.Converter)))
    print("")
    print("InvestmentUntil: "+str(value(2020+int(len(instance.PeriodActive)*LeapYearsInvestment))))
    print("Scenarios: "+str(len(instance.Scenario)))
    print("TotalOperationalHoursPerScenario: "+str(len(instance.Operationalhour)))
    print("TotalOperationalHoursPerInvYear: "+str(len(instance.Operationalhour)*len(instance.Scenario)))
    print("Seasons: "+str(len(instance.Season)))
    print("RegularSeasons: "+str(len(instance.FirstHoursOfRegSeason)))
    print("LengthRegSeason: "+str(value(instance.lengthRegSeason)))
    print("PeakSeasons: "+str(len(instance.FirstHoursOfPeakSeason)))
    print("LengthPeakSeason: "+str(value(instance.lengthPeakSeason)))
    print("")
    print("Discount rate: "+str(value(instance.discountrate)))
    print("Operational discount scale: "+str(value(instance.operationalDiscountrate)))
    print("--------------------------------------------------------------")

    if WRITE_LP:
        print("Writing LP-file...")
        start = time.time()
        lpstring = 'LP_' + name + '.lp'
        if USE_TEMP_DIR:
            lpstring = temp_dir + '/LP_'+ name + '.lp'
        instance.write(lpstring, io_options={'symbolic_solver_labels': True})
        end = time.time()
        print("Writing LP-file took [sec]:")
        print(end - start)

    print("Solving...")

    if solver == "CPLEX":
        opt = SolverFactory("cplex", Verbose=True)
        opt.options["lpmethod"] = 4
        opt.options["barrier crossover"] = -1
        #instance.display('outputs_cplex.txt')
    if solver == "Xpress":
        opt = SolverFactory("xpress") #Verbose=True
        opt.options["defaultAlg"] = 4
        opt.options["crossover"] = 0
        opt.options["lpLog"] = 1
        opt.options["Trace"] = 1
        #instance.display('outputs_xpress.txt')
    if solver == "Gurobi":
        opt = SolverFactory('gurobi', Verbose=True)
        opt.options["Crossover"]=0
        opt.options["Method"]=2

    results = opt.solve(instance, tee=True, logfile=result_file_path + '/logfile_' + name + '.log')#, keepfiles=True, symbolic_solver_labels=True)

    if PICKLE_INSTANCE:
        start = time.time()
        picklestring = 'instance' + name + '.pkl'
        if USE_TEMP_DIR:
            picklestring = temp_dir + '/instance' + name + '.pkl'
        with open(picklestring, mode='wb') as file:
            cloudpickle.dump(instance, file)
        end = time.time()
        print("Pickling instance took [sec]:")
        print(end - start)
            	
    #instance.display('outputs_gurobi.txt')

    #import pdb; pdb.set_trace()

    ###########
    ##RESULTS##
    ###########

    print("Writing results to .csv...")

    inv_per = []
    for i in instance.PeriodActive:
        my_string = str(value(2015+int(i)*LeapYearsInvestment))+"-"+str(value(2020+int(i)*LeapYearsInvestment))
        inv_per.append(my_string)

    f = open('results_objective.csv', 'a+', newline='')
    writer = csv.writer(f)
    writer.writerow([result_file_path, value(instance.Obj)])
    f.close()

    if HEATMODULE:
        f = open(result_file_path + "/" + 'results_output_conv.csv', 'w', newline='')
        writer = csv.writer(f)
        writer.writerow(["Node","ConverterType","Period","ConverterInvCap_MW","ConverterInstalledCap_MW","ConverterExpectedCapacityFactor","DiscountedInvestmentCost_Euro","ConverterExpectedAnnualHeatProduction_GWh"])
        for (n,r) in instance.ConverterOfNode:
            for i in instance.PeriodActive:
                writer.writerow([n,r,inv_per[int(i-1)],value(instance.ConverterInvCap[n,r,i]),value(instance.ConverterInstalledCap[n,r,i]), 
                value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.ConverterOperational[n,r,h,i,w] for (s,h) in instance.HoursOfSeason for w in instance.Scenario)/(instance.ConverterInstalledCap[n,r,i]*8760) if value(instance.ConverterInstalledCap[n,r,i]) != 0 else 0), 
                value(instance.discount_multiplier[i]*instance.ConverterInvCap[n,r,i]*instance.ConverterInvCost[r,i]), 
                value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.ConverterEff[r]*instance.convAvail[n,r,h,w,i]*instance.ConverterOperational[n,r,h,i,w] for (s,h) in instance.HoursOfSeason for w in instance.Scenario)/1000)])
        f.close()

        f = open(result_file_path + "/" + 'results_output_neigh.csv', 'w', newline='')
        writer = csv.writer(f)
        writer.writerow(["Node","NeighbourhoodType","Period","neighInvCap_MW","neighInstalledCap_MW","DiscountedInvestmentCost_Euro","neighExpectedElectricAnnualProduction_GWh","neighExpectedHeatAnnualProduction_GWh","neighExpectedConverterAnnualHeatProduction_GWh"])
        for (n,z) in instance.NeighbourhoodOfNode:
            for i in instance.PeriodActive:
                writer.writerow([n,z,inv_per[int(i-1)],value(instance.neighInvCap[n,z,i]),value(instance.neighInstalledCap[n,z,i]), 
                value(instance.discount_multiplier[i]*instance.neighInvCap[n,z,i]*instance.neighInvCost[z,i]), 
                value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.neighElectricOperational[n,z,h,i,w] for (s,h) in instance.HoursOfSeason for w in instance.Scenario)/1000), 
                value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.neighHeatOperational[n,z,h,i,w] for (s,h) in instance.HoursOfSeason for w in instance.Scenario)/1000), 
                value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.neighConverterEff[n,z,h,w]*instance.neighConverterOperational[n,z,h,i,w] for (s,h) in instance.HoursOfSeason for w in instance.Scenario)/1000)])
        f.close()

    f = open(result_file_path + "/" + 'results_output_gen.csv', 'w', newline='')
    writer = csv.writer(f)
    my_string = ["Node","GeneratorType","Period","genInvCap_MW","genInstalledCap_MW","genExpectedCapacityFactor","DiscountedInvestmentCost_Euro","genExpectedAnnualProduction_GWh"]
    if HEATMODULE:
        my_string.append("genExpectedAnnualHeatProduction_GWh")
    writer.writerow(my_string)
    for (n,g) in instance.GeneratorsOfNode:
        for i in instance.PeriodActive:
            my_string=[n,g,inv_per[int(i-1)],value(instance.genInvCap[n,g,i]),value(instance.genInstalledCap[n,g,i]), 
            value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.genOperational[n,g,h,i,w] for (s,h) in instance.HoursOfSeason for w in instance.Scenario)/(instance.genInstalledCap[n,g,i]*8760) if value(instance.genInstalledCap[n,g,i]) != 0 else 0), 
            value(instance.discount_multiplier[i]*instance.genInvCap[n,g,i]*instance.genInvCost[g,i])]
            if HEATMODULE:
                if g in instance.GeneratorEL:
                    my_string.append(value(sum(instance.seasScale[s]*instance.sceProbab[w]*instance.genCHPEfficiency[g,i]*instance.genOperational[n,g,h,i,w]/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario)))
                    if g in instance.GeneratorTR:
                        my_string.append(value(sum(instance.seasScale[s]*instance.sceProbab[w]*instance.genOperational[n,g,h,i,w]/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario)))
                    else:
                        my_string.append(0)
                else:
                    my_string.extend([0,value(sum(instance.seasScale[s]*instance.sceProbab[w]*instance.genOperational[n,g,h,i,w]/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario))]) 
            else:
                my_string.append(value(sum(instance.seasScale[s]*instance.sceProbab[w]*instance.genOperational[n,g,h,i,w]/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario)))
            writer.writerow(my_string)
    f.close()

    f = open(result_file_path + "/" + 'results_output_stor.csv', 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(["Node","StorageType","Period","storPWInvCap_MW","storPWInstalledCap_MW","storENInvCap_MWh","storENInstalledCap_MWh","DiscountedInvestmentCostPWEN_EuroPerMWMWh","ExpectedAnnualDischargeVolume_GWh","ExpectedAnnualLossesChargeDischarge_GWh"])
    for (n,b) in instance.StoragesOfNode:
        for i in instance.PeriodActive:
            writer.writerow([n,b,inv_per[int(i-1)],value(instance.storPWInvCap[n,b,i]),value(instance.storPWInstalledCap[n,b,i]), 
            value(instance.storENInvCap[n,b,i]),value(instance.storENInstalledCap[n,b,i]), 
            value(instance.discount_multiplier[i]*(instance.storPWInvCap[n,b,i]*instance.storPWInvCost[b,i] + instance.storENInvCap[n,b,i]*instance.storENInvCost[b,i])), 
            value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.storDischarge[n,b,h,i,w]/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario)), 
            value(sum(instance.sceProbab[w]*instance.seasScale[s]*((1 - instance.storageDischargeEff[b])*instance.storDischarge[n,b,h,i,w] + (1 - instance.storageChargeEff[b])*instance.storCharge[n,b,h,i,w])/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario))])
    f.close()

    f = open(result_file_path + "/" + 'results_output_transmision.csv', 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(["BetweenNode","AndNode","Period","transmisionInvCap_MW","transmisionInstalledCap_MW","DiscountedInvestmentCost_EuroPerMW","transmisionExpectedAnnualVolume_GWh","ExpectedAnnualLosses_GWh"])
    for (n1,n2) in instance.BidirectionalArc:
        for i in instance.PeriodActive:
            writer.writerow([n1,n2,inv_per[int(i-1)],value(instance.transmisionInvCap[n1,n2,i]),value(instance.transmisionInstalledCap[n1,n2,i]), 
            value(instance.discount_multiplier[i]*instance.transmisionInvCap[n1,n2,i]*instance.transmissionInvCost[n1,n2,i]), 
            value(sum(instance.sceProbab[w]*instance.seasScale[s]*(instance.transmisionOperational[n1,n2,h,i,w]+instance.transmisionOperational[n2,n1,h,i,w])/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario)), 
            value(sum(instance.sceProbab[w]*instance.seasScale[s]*((1 - instance.lineEfficiency[n1,n2])*instance.transmisionOperational[n1,n2,h,i,w] + (1 - instance.lineEfficiency[n2,n1])*instance.transmisionOperational[n2,n1,h,i,w])/1000 for (s,h) in instance.HoursOfSeason for w in instance.Scenario))])
    f.close()

    f = open(result_file_path + "/" + 'results_output_transmision_operational.csv', 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(["FromNode","ToNode","Period","Season","Scenario","Hour","TransmissionRecieved_MW","Losses_MW"])
    for (n1,n2) in instance.DirectionalLink:
        for i in instance.PeriodActive:
            for (s,h) in instance.HoursOfSeason:
                for w in instance.Scenario:
                    writer.writerow([n1,n2,inv_per[int(i-1)],s,w,h, 
                    value(instance.lineEfficiency[n1,n2]*instance.transmisionOperational[n1,n2,h,i,w]), 
                    value((1 - instance.lineEfficiency[n1,n2])*instance.transmisionOperational[n1,n2,h,i,w])])
    f.close()

    if HEATMODULE:
        f = open(result_file_path + "/" + 'results_output_OperationalEL.csv', 'w', newline='')
        writer = csv.writer(f)
        my_header = ["Node","Period","Scenario","Season","Hour","AllGen_MW","Load_MW","Net_load_MW"]
        for g in instance.GeneratorEL:
            my_string = str(g)+"_MW"
            my_header.append(my_string)
        my_header.append("Converter_MW")
        my_header.append("Neighbourhood_MW")
        if DRMODULE:
            my_header.extend(["DRCharge_MW","DRDischarge_MW","DREnergyLevel_MWh","DRMargCost_Euro"])
        my_header.extend(["storCharge_MW","storDischarge_MW","storEnergyLevel_MWh","LossesChargeDischargeBleed_MW","FlowOut_MW","FlowIn_MW","LossesFlowIn_MW","LoadShed_MW","Price_EURperMWh","AvgCO2_kgCO2perMWh"])    
        writer.writerow(my_header)
        for n in instance.Node:
            for i in instance.PeriodActive:
                for w in instance.Scenario:
                    for (s,h) in instance.HoursOfSeason:
                        my_string=[n,inv_per[int(i-1)],w,s,h, 
                        value(sum(instance.genCHPEfficiency[g,i]*instance.genOperational[n,g,h,i,w] for g in instance.GeneratorEL if (n,g) in instance.GeneratorsOfNode)), 
                        value(-instance.sload[n,h,i,w]), 
                        value(-(instance.sload[n,h,i,w] - instance.loadShed[n,h,i,w] + sum(instance.storCharge[n,b,h,i,w] - instance.storageDischargeEff[b]*instance.storDischarge[n,b,h,i,w] for b in instance.StorageEL if (n,b) in instance.StoragesOfNode) + 
                        sum(instance.transmisionOperational[n,link,h,i,w] - instance.lineEfficiency[link,n]*instance.transmisionOperational[link,n,h,i,w] for link in instance.NodesLinked[n])))]
                        for g in instance.GeneratorEL:
                            if (n,g) in instance.GeneratorsOfNode:
                                my_string.append(value(instance.genCHPEfficiency[g,i]*instance.genOperational[n,g,h,i,w]))
                            else:
                                my_string.append(0)
                        my_string.append(value(sum(-instance.ConverterOperational[n,r,h,i,w] for r in instance.Converter if (n,r) in instance.ConverterOfNode)))
                        my_string.append(value(sum(instance.neighElectricOperational[n,z,h,i,w]-instance.neighConverterOperational[n,z,h,i,w] for z in instance.Neighbourhood if (n,z) in instance.NeighbourhoodOfNode)))
                        if DRMODULE:
                            my_string.extend([value(sum(-instance.storCharge[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(instance.storDischarge[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(instance.storOperational[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(instance.storMargCost[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode))])
                        my_string.extend([value(sum(-instance.storCharge[n,b,h,i,w] for b in instance.StorageEL if (n,b) in instance.StoragesOfNode)), 
                        value(sum(instance.storDischarge[n,b,h,i,w] for b in instance.StorageEL if (n,b) in instance.StoragesOfNode)), 
                        value(sum(instance.storOperational[n,b,h,i,w] for b in instance.StorageEL if (n,b) in instance.StoragesOfNode)), 
                        value(sum(-(1 - instance.storageDischargeEff[b])*instance.storDischarge[n,b,h,i,w] - (1 - instance.storageChargeEff[b])*instance.storCharge[n,b,h,i,w] - (1 - instance.storageBleedEff[b])*instance.storOperational[n,b,h,i,w] for b in instance.StorageEL if (n,b) in instance.StoragesOfNode)), 
                        value(sum(-instance.transmisionOperational[n,link,h,i,w] for link in instance.NodesLinked[n])), 
                        value(sum(instance.transmisionOperational[link,n,h,i,w] for link in instance.NodesLinked[n])), 
                        value(sum(-(1 - instance.lineEfficiency[link,n])*instance.transmisionOperational[link,n,h,i,w] for link in instance.NodesLinked[n])), 
                        value(instance.loadShed[n,h,i,w]), 
                        value(instance.dual[instance.FlowBalance[n,h,i,w]]/(instance.operationalDiscountrate*instance.seasScale[s]*instance.sceProbab[w])), 
                        value(sum(instance.genCHPEfficiency[g,i]*instance.genOperational[n,g,h,i,w]*instance.genCO2TypeFactor[g]*(3.6/instance.genEfficiency[g,i]) for g in instance.GeneratorEL if (n,g) in instance.GeneratorsOfNode)/sum(instance.genOperational[n,g,h,i,w] for g in instance.GeneratorEL if (n,g) in instance.GeneratorsOfNode) if value(sum(instance.genOperational[n,g,h,i,w] for g in instance.GeneratorEL if (n,g) in instance.GeneratorsOfNode)) != 0 else 0)])
                        writer.writerow(my_string)
        f.close()

        f = open(result_file_path + "/" + 'results_output_OperationalTR.csv', 'w', newline='')
        writer = csv.writer(f)
        my_header = ["Node","Period","Scenario","Season","Hour","AllGen_MW","Load_MW","Net_load_MW"]
        for g in instance.GeneratorTR:
            my_string = str(g)+"_MW"
            my_header.append(my_string)
        for r in instance.Converter:
            my_string = str(r)+"_MW"
            my_header.append(my_string)
        for z in instance.Neighbourhood:
            my_string = str(z)+"_MW"
            my_header.append(my_string)
        my_header.extend(["storCharge_MW","storDischarge_MW","LossesChargeDischargeBleed_MW","LoadShedTR_MW","Price_EURperMWh","MargCO2_kgCO2perMWh","storEnergyLevel_MWh"])
        writer.writerow(my_header)
        for n in instance.Node:
            for i in instance.PeriodActive:
                for w in instance.Scenario:
                    for (s,h) in instance.HoursOfSeason:
                        if value(instance.sloadTR[n,h,i,w]) != 0:
                            my_string=[n,inv_per[int(i-1)],w,s,h, 
                            value(sum(instance.genOperational[n,g,h,i,w] for g in instance.GeneratorTR if (n,g) in instance.GeneratorsOfNode)), 
                            value(-instance.sloadTR[n,h,i,w]), 
                            value(-(instance.sloadTR[n,h,i,w] - instance.loadShedTR[n,h,i,w] + sum(instance.storCharge[n,b,h,i,w] - instance.storageDischargeEff[b]*instance.storDischarge[n,b,h,i,w] for b in instance.StorageTR if (n,b) in instance.StoragesOfNode)))]
                            for g in instance.GeneratorTR:
                                if (n,g) in instance.GeneratorsOfNode:
                                    my_string.append(value(instance.genOperational[n,g,h,i,w]))
                                else:
                                    my_string.append(0)
                            for r in instance.Converter:
                                if (n,r) in instance.ConverterOfNode:
                                    my_string.append(value(instance.ConverterEff[r]*instance.convAvail[n,r,h,w,i]*instance.ConverterOperational[n,r,h,i,w]))
                                else:
                                    my_string.append(0)
                            for z in instance.Neighbourhood:
                                if (n,z) in instance.NeighbourhoodOfNode:
                                    my_string.append(value(instance.neighHeatOperational[n,z,h,i,w]+instance.neighConverterEff[n,z,h,w]*instance.neighConverterOperational[n,z,h,i,w]))
                                else:
                                    my_string.append(0)
                            my_string.extend([value(sum(-instance.storCharge[n,b,h,i,w] for b in instance.StorageTR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(instance.storDischarge[n,b,h,i,w] for b in instance.StorageTR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(-(1 - instance.storageDischargeEff[b])*instance.storDischarge[n,b,h,i,w] - (1 - instance.storageChargeEff[b])*instance.storCharge[n,b,h,i,w] - (1 - instance.storageBleedEff[b])*instance.storOperational[n,b,h,i,w] for b in instance.StorageTR if (n,b) in instance.StoragesOfNode)), 
                            value(instance.loadShedTR[n,h,i,w]), 
                            value(instance.dual[instance.FlowBalanceTR[n,h,i,w]]/(instance.operationalDiscountrate*instance.seasScale[s]*instance.sceProbab[w])), 
                            value(sum(instance.genOperational[n,g,h,i,w]*instance.genCO2TypeFactor[g]*(3.6/instance.genEfficiency[g,i]) for g in instance.GeneratorTR if (n,g) in instance.GeneratorsOfNode)/sum(instance.genOperational[n,g,h,i,w] for g in instance.GeneratorTR if (n,g) in instance.GeneratorsOfNode) if value(sum(instance.genOperational[n,g,h,i,w] for g in instance.GeneratorTR if (n,g) in instance.GeneratorsOfNode)) != 0 else 0), 
                            value(sum(instance.storOperational[n,b,h,i,w] for b in instance.StorageTR if (n,b) in instance.StoragesOfNode))])
                            writer.writerow(my_string)
        f.close()
    else:
        f = open(result_file_path + "/" + 'results_output_Operational.csv', 'w', newline='')
        writer = csv.writer(f)
        my_header = ["Node","Period","Scenario","Season","Hour","AllGen_MW","Load_MW","Net_load_MW"]
        for g in instance.Generator:
            my_string = str(g)+"_MW"
            my_header.append(my_string)
        if DRMODULE:
            my_header.extend(["DRCharge_MW","DRDischarge_MW","DREnergyLevel_MWh","DRMargCost_Euro"])
        my_header.extend(["storCharge_MW","storDischarge_MW","storEnergyLevel_MWh","LossesChargeDischargeBleed_MW","FlowOut_MW","FlowIn_MW","LossesFlowIn_MW","LoadShed_MW","Price_EURperMWh","AvgCO2_kgCO2perMWh"])    
        writer.writerow(my_header)
        for n in instance.Node:
            for i in instance.PeriodActive:
                for w in instance.Scenario:
                    for (s,h) in instance.HoursOfSeason:
                        my_string=[n,inv_per[int(i-1)],w,s,h, 
                        value(sum(instance.genOperational[n,g,h,i,w] for g in instance.Generator if (n,g) in instance.GeneratorsOfNode)), 
                        value(-instance.sload[n,h,i,w]), 
                        value(-(instance.sload[n,h,i,w] - instance.loadShed[n,h,i,w] + sum(instance.storCharge[n,b,h,i,w] - instance.storageDischargeEff[b]*instance.storDischarge[n,b,h,i,w] for b in instance.Storage if (n,b) in instance.StoragesOfNode) + 
                        sum(instance.transmisionOperational[n,link,h,i,w] - instance.lineEfficiency[link,n]*instance.transmisionOperational[link,n,h,i,w] for link in instance.NodesLinked[n])))]
                        for g in instance.Generator:
                            if (n,g) in instance.GeneratorsOfNode:
                                my_string.append(value(instance.genOperational[n,g,h,i,w]))
                            else:
                                my_string.append(0)
                        if DRMODULE:
                            my_string.extend([value(sum(-instance.storCharge[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(instance.storDischarge[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(instance.storOperational[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode)), 
                            value(sum(instance.storMargCost[n,b,h,i,w] for b in instance.StorageDR if (n,b) in instance.StoragesOfNode))])
                        my_string.extend([value(sum(-instance.storCharge[n,b,h,i,w] for b in instance.Storage if (n,b) in instance.StoragesOfNode)), 
                        value(sum(instance.storDischarge[n,b,h,i,w] for b in instance.Storage if (n,b) in instance.StoragesOfNode)), 
                        value(sum(instance.storOperational[n,b,h,i,w] for b in instance.Storage if (n,b) in instance.StoragesOfNode)), 
                        value(sum(-(1 - instance.storageDischargeEff[b])*instance.storDischarge[n,b,h,i,w] - (1 - instance.storageChargeEff[b])*instance.storCharge[n,b,h,i,w] - (1 - instance.storageBleedEff[b])*instance.storOperational[n,b,h,i,w] for b in instance.Storage if (n,b) in instance.StoragesOfNode)), 
                        value(sum(-instance.transmisionOperational[n,link,h,i,w] for link in instance.NodesLinked[n])), 
                        value(sum(instance.transmisionOperational[link,n,h,i,w] for link in instance.NodesLinked[n])), 
                        value(sum(-(1 - instance.lineEfficiency[link,n])*instance.transmisionOperational[link,n,h,i,w] for link in instance.NodesLinked[n])), 
                        value(instance.loadShed[n,h,i,w]), 
                        value(instance.dual[instance.FlowBalance[n,h,i,w]]/(instance.operationalDiscountrate*instance.seasScale[s]*instance.sceProbab[w])), 
                        value(sum(instance.genOperational[n,g,h,i,w]*instance.genCO2TypeFactor[g]*(3.6/instance.genEfficiency[g,i]) for g in instance.Generator if (n,g) in instance.GeneratorsOfNode)/sum(instance.genOperational[n,g,h,i,w] for g in instance.Generator if (n,g) in instance.GeneratorsOfNode) if value(sum(instance.genOperational[n,g,h,i,w] for g in instance.Generator if (n,g) in instance.GeneratorsOfNode)) != 0 else 0)])
                        writer.writerow(my_string)
        f.close()

    f = open(result_file_path + "/" + 'results_output_curtailed_prod.csv', 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(["Node","RESGeneratorType","Period","ExpectedAnnualCurtailment_GWh"])
    for t in instance.Technology:
        if t == 'Hydro_ror' or t == 'Wind_onshr' or t == 'Wind_offshr' or t == 'Solar':
            for (n,g) in instance.GeneratorsOfNode:
                if (t,g) in instance.GeneratorsOfTechnology: 
                    for i in instance.PeriodActive:
                        writer.writerow([n,g,inv_per[int(i-1)], 
                        value(sum(instance.sceProbab[w]*instance.seasScale[s]*(instance.genCapAvail[n,g,h,w,i]*instance.genInstalledCap[n,g,i] - instance.genOperational[n,g,h,i,w])/1000 for w in instance.Scenario for (s,h) in instance.HoursOfSeason))])
    f.close()

    f = open(result_file_path + "/" + 'results_output_EuropePlot.csv', 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(["Period","genInstalledCap_MW"])
    my_string=[""]
    for g in instance.Generator:
        my_string.append(g)
    writer.writerow(my_string)
    my_string=["Initial"]
    for g in instance.Generator:
        my_string.append((value(sum(instance.genInitCap[n,g,1] for n in instance.Node if (n,g) in instance.GeneratorsOfNode))))
    writer.writerow(my_string)
    for i in instance.PeriodActive:
        my_string=[inv_per[int(i-1)]]
        for g in instance.Generator:
            my_string.append(value(sum(instance.genInstalledCap[n,g,i] for n in instance.Node if (n,g) in instance.GeneratorsOfNode)))
        writer.writerow(my_string)
    writer.writerow([""])
    writer.writerow(["Period","genExpectedAnnualProduction_GWh"])
    my_string=[""]
    for g in instance.Generator:
        my_string.append(g)
    writer.writerow(my_string)
    for i in instance.PeriodActive:
        my_string=[inv_per[int(i-1)]]
        for g in instance.Generator:
            my_string.append(value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.genOperational[n,g,h,i,w]/1000 for n in instance.Node if (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason for w in instance.Scenario)))
        writer.writerow(my_string)
    writer.writerow([""])
    writer.writerow(["Period","storPWInstalledCap_MW"])
    my_string=[""]
    for b in instance.Storage:
        my_string.append(b)
    writer.writerow(my_string)
    for i in instance.PeriodActive:
        my_string=[inv_per[int(i-1)]]
        for b in instance.Storage:
            my_string.append(value(sum(instance.storPWInstalledCap[n,b,i] for n in instance.Node if (n,b) in instance.StoragesOfNode)))
        writer.writerow(my_string)
    writer.writerow([""])
    writer.writerow(["Period","storENInstalledCap_MW"])
    my_string=[""]
    for b in instance.Storage:
        my_string.append(b)
    writer.writerow(my_string)
    for i in instance.PeriodActive:
        my_string=[inv_per[int(i-1)]]
        for b in instance.Storage:
            my_string.append(value(sum(instance.storENInstalledCap[n,b,i] for n in instance.Node if (n,b) in instance.StoragesOfNode)))
        writer.writerow(my_string)
    writer.writerow([""])
    writer.writerow(["Period","storExpectedAnnualDischarge_GWh"])
    my_string=[""]
    for b in instance.Storage:
        my_string.append(b)
    writer.writerow(my_string)
    for i in instance.PeriodActive:
        my_string=[inv_per[int(i-1)]]
        for b in instance.Storage:
            my_string.append(value(sum(instance.sceProbab[w]*instance.seasScale[s]*instance.storDischarge[n,b,h,i,w]/1000 for n in instance.Node if (n,b) in instance.StoragesOfNode for (s,h) in instance.HoursOfSeason for w in instance.Scenario)))
        writer.writerow(my_string)
    if HEATMODULE:
        writer.writerow([""])
        writer.writerow(["Period","ConverterInstalledCap_MW"])
        my_string=[""]
        for r in instance.Converter:
            my_string.append(r)
        writer.writerow(my_string)
        for i in instance.PeriodActive:
            my_string=[inv_per[int(i-1)]]
            for r in instance.Converter:
                my_string.append(value(sum(instance.ConverterInstalledCap[n,r,i] for n in instance.Node if (n,r) in instance.ConverterOfNode)))
            writer.writerow(my_string)
        writer.writerow([""])
        writer.writerow(["Period","NeighbourhoodInstalledCap_MW"])
        my_string=[""]
        for z in instance.Neighbourhood:
            my_string.append(z)
        writer.writerow(my_string)
        for i in instance.PeriodActive:
            my_string=[inv_per[int(i-1)]]
            for z in instance.Neighbourhood:
                my_string.append(value(sum(instance.neighInstalledCap[n,z,i] for n in instance.Node if (n,z) in instance.NeighbourhoodOfNode)))
            writer.writerow(my_string)
    f.close()

    f = open(result_file_path + "/" + 'results_output_EuropeSummary.csv', 'w', newline='')
    writer = csv.writer(f)
    writer.writerow(["Period","Scenario","AnnualCO2emission_Ton","CO2Price_EuroPerTon","CO2Cap_Ton","AnnualGeneration_GWh","AvgCO2factor_TonPerMWh","AvgELPrice_EuroPerMWh","TotAnnualCurtailedRES_GWh","TotAnnualLossesChargeDischarge_GWh","AnnualLossesTransmission_GWh"])
    for i in instance.PeriodActive:
        for w in instance.Scenario:
            my_string=[inv_per[int(i-1)],w, 
            value(sum(instance.seasScale[s]*instance.genOperational[n,g,h,i,w]*instance.genCO2TypeFactor[g]*(3.6/instance.genEfficiency[g,i]) for (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason))]
            if EMISSION_CAP:
                my_string.extend([value(instance.dual[instance.emission_cap[i,w]]/(instance.operationalDiscountrate*instance.sceProbab[w]*1e6)),value(instance.CO2cap[i]*1e6)])
            else:
                my_string.extend([value(instance.CO2price[i]),0])
            my_string.extend([value(sum(instance.seasScale[s]*instance.genOperational[n,g,h,i,w]/1000 for (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason)), 
            value(sum(instance.seasScale[s]*instance.genOperational[n,g,h,i,w]*instance.genCO2TypeFactor[g]*(3.6/instance.genEfficiency[g,i]) for (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason)/sum(instance.seasScale[s]*instance.genOperational[n,g,h,i,w] for (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason)), 
            value(sum(instance.dual[instance.FlowBalance[n,h,i,w]]/(instance.operationalDiscountrate*instance.seasScale[s]*instance.sceProbab[w]) for n in instance.Node for (s,h) in instance.HoursOfSeason)/value(len(instance.HoursOfSeason)*len(instance.Node))), 
            value(sum(instance.seasScale[s]*(instance.genCapAvail[n,g,h,w,i]*instance.genInstalledCap[n,g,i] - instance.genOperational[n,g,h,i,w])/1000 for (n,g) in instance.GeneratorsOfNode if g == 'Hydrorun-of-the-river' or g == 'Windonshore' or g == 'Windoffshore' or g == 'Solar' for (s,h) in instance.HoursOfSeason)), 
            value(sum(instance.seasScale[s]*((1 - instance.storageDischargeEff[b])*instance.storDischarge[n,b,h,i,w] + (1 - instance.storageChargeEff[b])*instance.storCharge[n,b,h,i,w])/1000 for (n,b) in instance.StoragesOfNode for (s,h) in instance.HoursOfSeason)), 
            value(sum(instance.seasScale[s]*((1 - instance.lineEfficiency[n1,n2])*instance.transmisionOperational[n1,n2,h,i,w] + (1 - instance.lineEfficiency[n2,n1])*instance.transmisionOperational[n2,n1,h,i,w])/1000 for (n1,n2) in instance.BidirectionalArc for (s,h) in instance.HoursOfSeason))])
            writer.writerow(my_string)
    writer.writerow([""])
    writer.writerow(["GeneratorType","Period","genInvCap_MW","genInstalledCap_MW","TotDiscountedInvestmentCost_Euro","genExpectedAnnualProduction_GWh"])
    for g in instance.Generator:
        for i in instance.PeriodActive:
            writer.writerow([g,inv_per[int(i-1)],value(sum(instance.genInvCap[n,g,i] for n in instance.Node if (n,g) in instance.GeneratorsOfNode)), 
            value(sum(instance.genInstalledCap[n,g,i] for n in instance.Node if (n,g) in instance.GeneratorsOfNode)), 
            value(sum(instance.discount_multiplier[i]*instance.genInvCap[n,g,i]*instance.genInvCost[g,i] for n in instance.Node if (n,g) in instance.GeneratorsOfNode)), 
            value(sum(instance.seasScale[s]*instance.sceProbab[w]*instance.genOperational[n,g,h,i,w]/1000 for n in instance.Node if (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason for w in instance.Scenario))])
    writer.writerow([""])
    writer.writerow(["StorageType","Period","storPWInvCap_MW","storPWInstalledCap_MW","storENInvCap_MWh","storENInstalledCap_MWh","TotDiscountedInvestmentCostPWEN_Euro","ExpectedAnnualDischargeVolume_GWh"])
    for b in instance.Storage:
        for i in instance.PeriodActive:
            writer.writerow([b,inv_per[int(i-1)],value(sum(instance.storPWInvCap[n,b,i] for n in instance.Node if (n,b) in instance.StoragesOfNode)), 
            value(sum(instance.storPWInstalledCap[n,b,i] for n in instance.Node if (n,b) in instance.StoragesOfNode)), 
            value(sum(instance.storENInvCap[n,b,i] for n in instance.Node if (n,b) in instance.StoragesOfNode)), 
            value(sum(instance.storENInstalledCap[n,b,i] for n in instance.Node if (n,b) in instance.StoragesOfNode)), 
            value(sum(instance.discount_multiplier[i]*(instance.storPWInvCap[n,b,i]*instance.storPWInvCost[b,i] + instance.storENInvCap[n,b,i]*instance.storENInvCost[b,i]) for n in instance.Node if (n,b) in instance.StoragesOfNode)), 
            value(sum(instance.seasScale[s]*instance.sceProbab[w]*instance.storDischarge[n,b,h,i,w]/1000 for n in instance.Node if (n,b) in instance.StoragesOfNode for (s,h) in instance.HoursOfSeason for w in instance.Scenario))])
    f.close()
    
    #Print first stage decisions for out-of-sample
    f = open(result_file_path + "/" + 'genInvCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["Node","Generator","Period","genInvCap"])
    for (n,g) in instance.GeneratorsOfNode:
        for i in instance.PeriodActive:
            writer.writerow([n,g,i,value(instance.genInvCap[n,g,i])])
    f.close()
    
    f = open(result_file_path + "/" + 'transmisionInvCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["FromNode","ToNode","Period","transmisionInvCap"])
    for (n1,n2) in instance.BidirectionalArc:
        for i in instance.PeriodActive:
            writer.writerow([n1,n2,i,value(instance.transmisionInvCap[n1,n2,i])])
    f.close()
    
    f = open(result_file_path + "/" + 'storPWInvCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["Node","Storage","Period","storPWInvCap"])
    for (n,b) in instance.StoragesOfNode:
        for i in instance.PeriodActive:
            writer.writerow([n,b,i,value(instance.storPWInvCap[n,b,i])])
    f.close()
    
    f = open(result_file_path + "/" + 'storENInvCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["Node","Storage","Period","storENInvCap"])
    for (n,b) in instance.StoragesOfNode:
        for i in instance.PeriodActive:
            writer.writerow([n,b,i,value(instance.storENInvCap[n,b,i])])
    f.close()
    
    f = open(result_file_path + "/" + 'genInstalledCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["Node","Generator","Period","genInstalledCap"])
    for (n,g) in instance.GeneratorsOfNode:
        for i in instance.PeriodActive:
            writer.writerow([n,g,i,value(instance.genInstalledCap[n,g,i])])
    f.close()
    
    f = open(result_file_path + "/" + 'transmisionInstalledCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["FromNode","ToNode","Period","transmisionInstalledCap"])
    for (n1,n2) in instance.BidirectionalArc:
        for i in instance.PeriodActive:
            writer.writerow([n1,n2,i,value(instance.transmisionInstalledCap[n1,n2,i])])
    f.close()
    
    f = open(result_file_path + "/" + 'storPWInstalledCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["Node","Storage","Period","storPWInstalledCap"])
    for (n,b) in instance.StoragesOfNode:
        for i in instance.PeriodActive:
            writer.writerow([n,b,i,value(instance.storPWInstalledCap[n,b,i])])
    f.close()
    
    f = open(result_file_path + "/" + 'storENInstalledCap.tab', 'w', newline='')
    writer = csv.writer(f, delimiter='\t')
    writer.writerow(["Node","Storage","Period","storENInstalledCap"])
    for (n,b) in instance.StoragesOfNode:
        for i in instance.PeriodActive:
            writer.writerow([n,b,i,value(instance.storENInstalledCap[n,b,i])])
    f.close()
    
    if IAMC_PRINT:
        ####################
        ###STANDARD PRINT###
        ####################
        
        import pandas as pd
        
        Modelname = "EMPIRE"
        Scenario = "1.5degree"

        dict_countries = {"Austria": "Austria",
                          "Bosnia and Herzegovina": "BosniaH",
                          "Belgium": "Belgium", "Bulgaria": "Bulgaria",
                          "Switzerland": "Switzerland", 
                          "Czech Republic": "CzechR", "Germany": "Germany",
                          "Denmark": "Denmark", "Estonia": "Estonia", 
                          "Spain": "Spain", "Finland": "Finland",
                          "France": "France", "United Kingdom": "GreatBrit.",
                          "Greece": "Greece", "Croatia": "Croatia", 
                          "Hungary": "Hungary", "Ireland": "Ireland", 
                          "Italy": "Italy", "Lithuania": "Lithuania",
                          "Luxembourg": "Luxemb.", "Latvia": "Latvia",
                          "North Macedonia": "Macedonia", 
                          "The Netherlands": "Netherlands", "Norway": "Norway",
                          "Poland": "Poland", "Portugal": "Portugal",
                          "Romania": "Romania", "Serbia": "Serbia", 
                          "Sweden": "Sweden", "Slovenia": "Slovenia",
                          "Slovakia": "Slovakia", "Norway|Ostland": "NO1", 
                          "Norway|Sorland": "NO2", "Norway|Norgemidt": "NO3",
                          "Norway|Troms": "NO4", "Norway|Vestmidt": "NO5"}

        dict_countries_reversed = dict([reversed(i) for i in dict_countries.items()])

        dict_generators = {"Bio": "Biomass", "Bioexisting": "Biomass",
                           "Coalexisting": "Coal|w/o CCS",
                           "Coal": "Coal|w/o CCS", "CoalCCS": "Coal|w/ CCS",
                           "CoalCCSadv": "Coal|w/ CCS", 
                           "Lignite": "Lignite|w/o CCS",
                           "Liginiteexisting": "Lignite|w/o CCS", 
                           "LigniteCCSadv": "Lignite|w/ CCS", 
                           "Gasexisting": "Gas|CCGT|w/o CCS", 
                           "GasOCGT": "Gas|OCGT|w/o CCS", 
                           "GasCCGT": "Gas|CCGT|w/o CCS", 
                           "GasCCS": "Gas|CCGT|w/ CCS", 
                           "GasCCSadv": "Gas|CCGT|w/ CCS", 
                           "Oilexisting": "Oil", "Nuclear": "Nuclear", 
                           "Wave": "Ocean", "Geo": "Geothermal", 
                           "Hydroregulated": "Hydro|Reservoir", 
                           "Hydrorun-of-the-river": "Hydro|Run-of-River", 
                           "Windonshore": "Wind|Onshore", 
                           "Windoffshore": "Wind|Offshore",
                           "Windoffshoregrounded": "Wind|Offshore", 
                           "Windoffshorefloating": "Wind|Offshore", 
                           "Solar": "Solar|PV", "Waste": "Waste", 
                           "Bio10cofiring": "Coal|w/o CCS", 
                           "Bio10cofiringCCS": "Coal|w/ CCS", 
                           "LigniteCCSsup": "Lignite|w/ CCS"}
        
        #Make datetime from HoursOfSeason       
        seasonstart={"winter": '2020-01-01',
                     "spring": '2020-04-01',
                     "summer": '2020-07-01',
                     "fall": '2020-10-01',
                     "peak1": '2020-11-01',
                     "peak2": '2020-12-01'}
        
        seasonhours=[]
    
        for s in instance.Season:
            if s not in 'peak':
                t=pd.to_datetime(list(range(lengthRegSeason)), unit='h', origin=pd.Timestamp(seasonstart[s]))
                t=[str(i)[5:-3] for i in t]
                t=[str(i)+"+01:00" for i in t]
                seasonhours+=t
            else:
                t=pd.to_datetime(list(range(lengthPeakSeason)), unit='h', origin=pd.Timestamp(seasonstart[s]))
                t=[str(i)[5:-3] for i in t]
                t=[str(i)+"+01:00" for i in t]
                seasonhours+=t       
        
        #Scalefactors to make units
        Mtonperton = (1/1000000)

        GJperMWh = 3.6
        EJperMWh = 3.6*10**(-9)

        GWperMW = (1/1000)

        USD10perEUR10 = 1.33 #Source: https://www.statista.com/statistics/412794/euro-to-u-s-dollar-annual-average-exchange-rate/ 
        EUR10perEUR18 = 154/171 #Source: https://www.inflationtool.com/euro 
        USD10perEUR18 = USD10perEUR10*EUR10perEUR18 

        print("Writing standard output to .csv...")
        
        f = pd.DataFrame(columns=["model", "scenario", "region", "variable", "unit", "subannual"]+[value(2020+(i)*instance.LeapYearsInvestment) for i in instance.PeriodActive])

        def row_write(df, region, variable, unit, subannual, input_value, scenario=Scenario, modelname=Modelname):
            df2 = pd.DataFrame([[modelname, scenario, region, variable, unit, subannual]+input_value],
                               columns=["model", "scenario", "region", "variable", "unit", "subannual"]+[value(2020+(i)*instance.LeapYearsInvestment) for i in instance.PeriodActive])
            df = pd.concat([df, df2], ignore_index=True)
            return df

        f = row_write(f, "Europe", "Discount rate|Electricity", "%", "Year", [value(instance.discountrate*100)]*len(instance.PeriodActive)) #Discount rate
        f = row_write(f, "Europe", "Capacity|Electricity", "GW", "Year", [value(sum(instance.genInstalledCap[n,g,i]*GWperMW for (n,g) in instance.GeneratorsOfNode)) for i in instance.PeriodActive]) #Total European installed generator capacity 
        f = row_write(f, "Europe", "Investment|Energy Supply|Electricity", "billion US$2010/yr", "Year", [value((1/instance.LeapYearsInvestment)*USD10perEUR18* \
                    sum(instance.genInvCost[g,i]*instance.genInvCap[n,g,i] for (n,g) in instance.GeneratorsOfNode) + \
                    sum(instance.transmissionInvCost[n1,n2,i]*instance.transmisionInvCap[n1,n2,i] for (n1,n2) in instance.BidirectionalArc) + \
                    sum((instance.storPWInvCost[b,i]*instance.storPWInvCap[n,b,i]+instance.storENInvCost[b,i]*instance.storENInvCap[n,b,i]) for (n,b) in instance.StoragesOfNode)) for i in instance.PeriodActive]) #Total European investment cost (gen+stor+trans)
        f = row_write(f, "Europe", "Investment|Energy Supply|Electricity|Electricity storage", "billion US$2010/yr", "Year", [value((1/instance.LeapYearsInvestment)*USD10perEUR18* \
                    sum((instance.storPWInvCost[b,i]*instance.storPWInvCap[n,b,i]+instance.storENInvCost[b,i]*instance.storENInvCap[n,b,i]) for (n,b) in instance.StoragesOfNode)) for i in instance.PeriodActive]) #Total European storage investment cost
        f = row_write(f, "Europe", "Investment|Energy Supply|Electricity|Transmission and Distribution", "billion US$2010/yr", "Year", [value((1/instance.LeapYearsInvestment)*USD10perEUR18* \
                    sum(instance.transmissionInvCost[n1,n2,i]*instance.transmisionInvCap[n1,n2,i] for (n1,n2) in instance.BidirectionalArc)) for i in instance.PeriodActive]) #Total European transmission investment cost
        for w in instance.Scenario:
            f = row_write(f, "Europe", "Emissions|CO2|Energy|Supply|Electricity", "Mt CO2/yr", "Year", [value(Mtonperton*sum(instance.seasScale[s]*instance.genCO2TypeFactor[g]*(GJperMWh/instance.genEfficiency[g,i])* \
                    instance.genOperational[n,g,h,i,w] for (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason)) for i in instance.PeriodActive], Scenario+"|"+str(w)) #Total European emissions per scenario
            f = row_write(f, "Europe", "Secondary Energy|Electricity", "EJ/yr", "Year", \
                    [value(sum(EJperMWh*instance.seasScale[s]*instance.genOperational[n,g,h,i,w] for (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason)) for i in instance.PeriodActive], Scenario+"|"+str(w)) #Total European generation per scenario
            for g in instance.Generator:
                f = row_write(f, "Europe", "Active Power|Electricity|"+dict_generators[str(g)], "MWh", "Year", \
                    [value(sum(instance.seasScale[s]*instance.genOperational[n,g,h,i,w] for n in instance.Node if (n,g) in instance.GeneratorsOfNode for (s,h) in instance.HoursOfSeason)) for i in instance.PeriodActive], Scenario+"|"+str(w)) #Total generation per type and scenario
            for (s,h) in instance.HoursOfSeason:
                for n in instance.Node:
                    f = row_write(f, dict_countries_reversed[str(n)], "Price|Secondary Energy|Electricity", "US$2010/GJ", seasonhours[h-1], \
                        [value(instance.dual[instance.FlowBalance[n,h,i,w]]/(GJperMWh*instance.operationalDiscountrate*instance.seasScale[s]*instance.sceProbab[w])) for i in instance.PeriodActive], Scenario+"|"+str(w)+str(s))
        for g in instance.Generator:
            f = row_write(f, "Europe", "Capacity|Electricity|"+dict_generators[str(g)], "GW", "Year", [value(sum(instance.genInstalledCap[n,g,i]*GWperMW for n in instance.Node if (n,g) in instance.GeneratorsOfNode)) for i in instance.PeriodActive]) #Total European installed generator capacity per type
            f = row_write(f, "Europe", "Capital Cost|Electricity|"+dict_generators[str(g)], "US$2010/kW", "Year", [value(instance.genCapitalCost[g,i]*USD10perEUR18) for i in instance.PeriodActive]) #Capital generator cost
            if value(instance.genMargCost[g,instance.PeriodActive[1]]) != 0: 
                f = row_write(f, "Europe", "Variable Cost|Electricity|"+dict_generators[str(g)], "EUR/MWh", "Year", [value(instance.genMargCost[g,i]) for i in instance.PeriodActive])
            f = row_write(f, "Europe", "Investment|Energy Supply|Electricity|"+dict_generators[str(g)], "billion US$2010/yr", "Year", [value((1/instance.LeapYearsInvestment)*USD10perEUR18* \
                    sum(instance.genInvCost[g,i]*instance.genInvCap[n,g,i] for n in instance.Node if (n,g) in instance.GeneratorsOfNode)) for i in instance.PeriodActive]) #Total generator investment cost per type
            if value(instance.genCO2TypeFactor[g]) != 0:
                f = row_write(f, "Europe", "CO2 Emmissions|Electricity|"+dict_generators[str(g)], "tons/MWh", "Year", [value(instance.genCO2TypeFactor[g]*(GJperMWh/instance.genEfficiency[g,i])) for i in instance.PeriodActive]) #CO2 factor per generator type
        for (n,g) in instance.GeneratorsOfNode:
            f = row_write(f, dict_countries_reversed[str(n)], "Capacity|Electricity|"+dict_generators[str(g)], "GW", "Year", [value(instance.genInstalledCap[n,g,i]*GWperMW) for i in instance.PeriodActive]) #Installed generator capacity per country and type
        
        f = f.groupby(['model','scenario','region','variable','unit','subannual']).sum().reset_index() #NB! DOES NOT WORK FOR UNIT COSTS; SHOULD BE FIXED
        
        if not os.path.exists(result_file_path + "/" + 'IAMC'):
            os.makedirs(result_file_path + "/" + 'IAMC')
        f.to_csv(result_file_path + "/" + 'IAMC/empire_iamc.csv', index=None)
