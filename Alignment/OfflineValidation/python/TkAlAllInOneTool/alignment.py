import configTemplates
from helperFunctions import replaceByMap, parsecolor, parsestyle
import os
import re
from TkAlExceptions import AllInOneError

class Alignment:
    def __init__(self, name, config, runGeomComp = "1"):
        self.condShorts = {
            "TrackerAlignmentErrorExtendedRcd": {
                "zeroAPE": {
                    "connectString":("frontier://FrontierProd"
                                             "/CMS_CONDITIONS"),
                    "tagName": "TrackerIdealGeometryErrorsExtended210_mc",
                    "labelName": ""
                }
            },
            "TrackerSurfaceDeformationRcd": {
                "zeroDeformations": {
                    "connectString":("frontier://FrontierProd"
                                             "/CMS_CONDITIONS"),
                    "tagName": "TrackerSurfaceDeformations_zero",
                    "labelName": ""
                }
            },
        }
        section = "alignment:%s"%name
        if not config.has_section( section ):
            raise AllInOneError("section %s not found. Please define the "
                                  "alignment!"%section)
        config.checkInput(section,
                          knownSimpleOptions = ['globaltag', 'style', 'color', 'title', 'mp', 'hp', 'sm'],
                          knownKeywords = ['condition'])
        self.name = name
        if config.exists(section,"title"):
            self.title = config.get(section,"title")
        else:
            self.title = self.name
        if (int(runGeomComp) != 1):
            self.name += "_run" + runGeomComp
            self.title += " run " + runGeomComp
        if "|" in self.title or "," in self.title or '"' in self.title:
            msg = "The characters '|', '\"', and ',' cannot be used in the alignment title!"
            raise AllInOneError(msg)
        self.runGeomComp = runGeomComp
        self.globaltag = config.get( section, "globaltag" )
        self.conditions = self.__getConditions( config, section )

        self.color = config.get(section,"color")
        self.style = config.get(section,"style")

        self.color = str(parsecolor(self.color))
        self.style = str(parsestyle(self.style))
        
    def __shorthandExists(self, theRcdName, theShorthand):
        """Method which checks, if `theShorthand` is a valid shorthand for the
        given `theRcdName`.
        
        Arguments:
        - `theRcdName`: String which specifies the database record.
        - `theShorthand`: String which specifies the shorthand to check.
        """

        if (theRcdName in self.condShorts) and \
                (theShorthand in self.condShorts[theRcdName]):
            return True
        else:
            return False

    def __getConditions( self, theConfig, theSection ):
        conditions = []
        for option in theConfig.options( theSection ):
            if option == "mp":
                condPars = theConfig.get(theSection, option).split(",")
                if len(condPars) > 1:
                    raise AllInOneError("Only one argument accepted for mp (should be the job number)")
                number, = condPars
                folder = "/afs/cern.ch/cms/CAF/CMSALCA/ALCA_TRACKERALIGN/MP/MPproduction/{}{}/".format(option, number)
                if not os.path.exists(folder):
                    raise AllInOneError(folder+" does not exist.")
                dbfile = os.path.join(folder, "jobData/jobm/alignments_MP.db")
                if not os.path.exists(dbfile):
                    raise AllInOneError("No file {}.  Maybe your alignment folder is corrupted?".format(dbfile))
                conditions.append({"rcdName": "TrackerAlignmentRcd",
                                   "connectString": "sqlite_file:"+dbfile,
                                   "tagName": "Alignments",
                                   "labelName": ""})
                conditions.append({"rcdName": "TrackerSurfaceDeformationRcd",
                                   "connectString": "sqlite_file:"+dbfile,
                                   "tagName": "Deformations",
                                   "labelName": ""})

            elif option in ("hp", "sm"):
                condPars = theConfig.get(theSection, option).split(",")
                condPars = [_.strip() for _ in condPars]
                if len(condPars) == 1:
                    number, = condPars
                    iteration = None
                elif len(condPars) == 2:
                    number, iteration = condPars
                else:
                    raise AllInOneError("Up to 2 arguments accepted for {} (job number, and optionally iteration)".format(option))
                folder = "/afs/cern.ch/cms/CAF/CMSALCA/ALCA_TRACKERALIGN2/HipPy/alignments/{}{}".format(option, number)
                if not os.path.exists(folder):
                    raise AllInOneError(folder+" does not exist.")
                if iteration is None:
                    for filename in os.listdir(folder):
                        match = re.match("alignments_iter([0-9]*).db", filename)
                        if match:
                            if iteration is None or int(match.group(1)) > iteration:
                                iteration = int(match.group(1))
                    if iteration is None:
                        raise AllInOneError("No alignments in {}".format(folder))
                dbfile = os.path.join(folder, "alignments_iter{}.db".format(iteration))
                if not os.path.exists(dbfile):
                    raise AllInOneError("No file {}.".format(dbfile))
                conditions.append({"rcdName": "TrackerAlignmentRcd",
                                   "connectString": "sqlite_file:"+dbfile,
                                   "tagName": "Alignments",
                                   "labelName": ""})

            elif option.startswith( "condition " ):
                rcdName = option.split( "condition " )[1]
                condPars = theConfig.get( theSection, option ).split( "," )
                if len(condPars) == 1:
                    if len(condPars[0])==0:
                        msg = ("In section [%s]: '%s' is used with too few "
                               "arguments. A connect_string and a tag are "
                               "required!"%(theSection, option))
                        raise AllInOneError(msg)
                    elif self.__shorthandExists(rcdName, condPars[0]):
                        shorthand = condPars[0]
                        condPars = [
                            self.condShorts[rcdName][shorthand]["connectString"],
                            self.condShorts[rcdName][shorthand]["tagName"],
                            self.condShorts[rcdName][shorthand]["labelName"]]
                    else:
                        msg = ("In section [%s]: '%s' is used with '%s', "
                               "which is an unknown shorthand for '%s'. Either "
                               "provide at least a connect_string and a tag or "
                               "use a known shorthand.\n"
                               %(theSection, option, condPars[0], rcdName))
                        if rcdName in self.condShorts:
                            msg += "Known shorthands for '%s':\n"%(rcdName)
                            theShorts = self.condShorts[rcdName]
                            knownShorts = [("\t"+key+": "
                                            +theShorts[key]["connectString"]+","
                                            +theShorts[key]["tagName"]+","
                                            +theShorts[key]["labelName"]) \
                                               for key in theShorts]
                            msg+="\n".join(knownShorts)
                        else:
                            msg += ("There are no known shorthands for '%s'."
                                    %(rcdName))
                        raise AllInOneError(msg)
                if len( condPars ) == 2:
                    condPars.append( "" )
                if len(condPars) > 3:
                    msg = ("In section [%s]: '%s' is used with too many "
                           "arguments. A maximum of 3 arguments is allowed."
                           %(theSection, option))
                    raise AllInOneError(msg)
                conditions.append({"rcdName": rcdName.strip(),
                                   "connectString": condPars[0].strip(),
                                   "tagName": condPars[1].strip(),
                                   "labelName": condPars[2].strip()})
        return conditions

    def __testDbExist(self, dbpath):
        #FIXME delete return to end train debuging
        return
        if not dbpath.startswith("sqlite_file:"):
            print "WARNING: could not check existence for",dbpath
        else:
            if not os.path.exists( dbpath.split("sqlite_file:")[1] ):
                raise "could not find file: '%s'"%dbpath.split("sqlite_file:")[1]
 
    def restrictTo( self, restriction ):
        result = []
        if not restriction == None:
            for mode in self.mode:
                if mode in restriction:
                    result.append( mode )
            self.mode = result

    def getRepMap( self ):
        result = {
            "name": self.name,
            "title": self.title,
            "color": self.color,
            "style": self.style,
            "runGeomComp": self.runGeomComp,
            "GlobalTag": self.globaltag
            }
        return result  

    def getConditions(self):
        """This function creates the configuration snippet to override
           global tag conditions.
           """
        if len( self.conditions ):
            loadCond = ("\nimport CalibTracker.Configuration."
                        "Common.PoolDBESSource_cfi\n")
            for cond in self.conditions:
                if not cond["labelName"] == "":
                    temp = configTemplates.conditionsTemplate.replace(
                        "tag = cms.string('.oO[tagName]Oo.')",
                        ("tag = cms.string('.oO[tagName]Oo.'),"
                         "\nlabel = cms.untracked.string('.oO[labelName]Oo.')"))
                else:    
                    temp = configTemplates.conditionsTemplate
                loadCond += replaceByMap( temp, cond )
        else:
            loadCond = ""
        return loadCond
