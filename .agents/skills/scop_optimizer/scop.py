#default_exp scop

#hide
#from nbdev.showdoc import *

#export
import sys
import re
import copy
import platform
import string
_trans = str.maketrans("-+*/'(){}^=<>$ | #?,\ ", "_"*22) #文字列変換用
import ast
import pickle
import datetime as dt
from collections import Counter
from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import List, Tuple, Any, ClassVar, Literal, Optional, Dict, Set, Union

#以下非標準ファイル
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly
import plotly.figure_factory as ff
from plotly.subplots import make_subplots


#hide
from IPython.display import Image, YouTubeVideo
folder = "../data/scop/"

#hide_input
#Image("../figure/scopclass.jpg", width=500)

#export
def plot_scop(file_name: str="scop_out.txt"):
    with open(file_name) as f:
        out = f.readlines()
    x, y1, y2 = [],[],[] 
    for l in out[5:]: 
        sep = re.split("[=()/]", l)
        #print(sep)
        if sep[0] == '# penalty ':
            break
        if sep[0] == 'penalty ':
            hard, soft, cpu = map(float, [ sep[1], sep[2], sep[6]])
            x.append(cpu)
            y1.append(hard)
            y2.append(soft)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
            x = x, 
            y = y1,
            mode='markers+lines',
            name= "hard",
            marker=dict(
                size=10,
                color= "red")
    ))
    fig.add_trace(go.Scatter(
            x = x, 
            y = y2,
            name ="soft",
            mode='markers+lines',
            marker=dict(
                size=8,
                color= "blue")
    ))
    fig.update_layout(title = "SCOP performance",
                   xaxis_title='CPU time',
                   yaxis_title='Penalty')
    return fig

# fig = plot_scop()
# plotly.offline.plot(fig);

#hide_input
#Image("../figure/plot-scop.png")

#export
class Parameters(BaseModel):
    """
    SCOP parameter class to control the operation of SCOP.

    - TimeLimit: Limits the total time expended (in seconds). Positive integer. Default = 600.
    - OutputFlag: Controls the output log. Boolean. Default = False.
    - RandomSeed: Sets the random seed number. Integer. Default = 1.
    - Target: Sets the target penalty value;
            optimization will terminate if the solver determines that the optimum penalty value
            for the model is worse than the specified "Target." Non-negative integer. Default = 0.
    - Initial: True if you want to solve the problem starting with an initial solution obtained before, False otherwise. Default = False.
    """
    TimeLimit: int = 600
    OutputFlag: int = 0
    RandomSeed: int = 1
    Target: int = 0
    Initial: bool = False

    def __str__(self):
        return f" TimeLimit = {self.TimeLimit} \n OutputFlag = {self.OutputFlag} \n RandomSeed = {self.RandomSeed} \n Taeget = {self.Target} \n Initial = {self.Initial}"

#hide
#show_doc(Parameters)

params = Parameters()
params.TimeLimit = 3 
print(params)

#export
class Variable(BaseModel):
    """
    SCOP variable class. Variables are associated with a particular model.
    You can create a variable object by adding a variable to a model (using Model.addVariable or Model.addVariables)
    instead of by using a Variable constructor.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[Any] = ""
    domain: List[Any] = Field(default_factory=list)
    value: Any = None

    ID: ClassVar[int] = 0 #variable ID for anonymous variables

    def __init__(self, name="", domain=None):
        if domain is None:
            domain = []
        super().__init__(name=name, domain=domain)

    @model_validator(mode='after')
    def init_variable(self) -> 'Variable':
        if self.name == "" or self.name is None:
            self.name = f"__x{Variable.ID}"
            Variable.ID += 1
        if not isinstance(self.name, str):
            raise ValueError("Variable name must be a string")
        self.name = str(self.name).translate(_trans)
        self.domain = [str(d) for d in self.domain]
        return self

    def __str__(self):
        return "variable {0}:{1} = {2}".format(
            str(self.name), str(self.domain), str(self.value)
            )

    def __hash__(self):
        return hash(self.name)

#hide
#show_doc(Variable)

#標準的な使用法
var = Variable("X[1]", [1,2,3])
print(var)

#無記名の例
var1 = Variable(domain = [1,2,3])
var2 = Variable(domain = [4,5,6])
print(var1)
print(var2)

#変数名に数字をいれた場合
try:
    var1 = Variable(name = 1, domain = [1,2,3])
except ValueError as error:
    print(error)

#export
class Model(BaseModel):
    """
    SCOP model class.

    Attbibutes:
    - constraints: Set of constraint objects in the model.
    - variables: Set of variable objects in the model.
    - Params:  Object including all the parameters of the model.
    - varDict: Dictionary that maps variable names to the variable object.

    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = ""
    constraints: List[Any] = Field(default_factory=list)
    variables: List[Variable] = Field(default_factory=list)
    Params: Parameters = Field(default_factory=Parameters)
    varDict: Dict[str, Variable] = Field(default_factory=dict)
    Status: int = 10      # unsolved

    def __init__(self, name=""):
        super().__init__(name=name)
    def __str__(self):
        """
            return the information of the problem
            constraints are expanded and are shown in a readable format
        """
        ret = ["Model:"+str(self.name) ]
        ret.append( "number of variables = {0} ".format(len(self.variables)) )
        ret.append( "number of constraints= {0} ".format(len(self.constraints)) )
        for v in self.variables:
            ret.append(str(v))

        for c in self.constraints:
            ret.append("{0} :LHS ={1} ".format(str(c)[:-1], str(c.lhs)) )
        return " \n".join(ret)

    def update(self):
        """
        prepare a string representing the current model in the scop input format
        """
        f  = [ ]
        #variable declarations
        for var in self.variables:
            domainList = ",".join([str(i) for i in var.domain])
            f.append( "variable %s in { %s } \n" % (var.name, domainList) )
        #target value declaration
        f.append( "target = %s \n" % str(self.Params.Target) )
        #constraint declarations
        for con in self.constraints:
            f.append(str(con))
        return " ".join(f)

    def addVariable(self, name="", domain=[]):
        """
        - addVariable ( name="", domain=[] )
          Add a variable to the model.

        Arguments:
        - name: Name for new variable. A string object.
        - domain: Domain (list of values) of new variable. Each value must be a string or numeric object.

        Return value:
        New variable object.

        Example usage:
        x = model.addVarriable("var")                     # domain  is set to []
        x = model.addVariable(name="var",domain=[1,2,3])  # arguments by name
        x = model.addVariable("var",["A","B","C"])        # arguments by position

        """
        var =Variable(name,domain)
        # keep variable names using the dictionary varDict
        # to check the validity of constraints later
        # check the duplicated name
        if var.name in self.varDict:
            raise ValueError("duplicate key '{0}' found in variable name".format(var.name))
        else:
            self.variables.append(var)
            self.varDict[var.name]=var
        return var

    def addVariables(self, names=[], domain=[]):
        """
        - addVariables(names=[], domain=[])
           Add variables and their (identical) domain.

        Arguments:
        - names: list of new variables. A list of string objects.
        - domain: Domain (list of values) of new variables. Each value must be a string or numeric object.

        Return value:
        List of new variable objects.

        Example usage:
        varlist=["var1","var2","var3"]
        x = model.addVariables(varlist)                      # domain  is set to []
        x = model.addVariables(names=varlist,domain=[1,2,3]  # arguments by name
        x = model.addVariables(varlist,["A","B","C"]         # arguments by position

        """
        if type(names)!=type([]):
            raise TypeError("The first argument (names) must be a list.")
        varlist=[]
        for var in names:
            varlist.append(self.addVariable(var,domain))
        return varlist

    def addConstraint(self, con):
        """
        addConstraint ( con )
        Add a constraint to the model.

        Argument:
        - con: A constraint object (Linear, Quadratic or AllDiff).

        Example usage:
        model.addConstraint(L)

        """
        if not isinstance(con,Constraint):
            raise TypeError("error: %r should be a subclass of Constraint" % con)

        #check the feasibility of the constraint added in the class con
        try:
            if con.feasible(self.varDict):
                self.constraints.append(con)
        except NameError:
            raise  NameError("Consrtaint %r has an error " % con )

##    def addConstraints(self,*cons):
##        for c in cons:
##            self.addConstraint(c)

    def optimize(self):
        """
        optimize ()
        Optimize the model using scop.exe in the same directory.

        Example usage:
        model.optimize()
        """

        time=self.Params.TimeLimit
        seed=self.Params.RandomSeed
        LOG=self.Params.OutputFlag

        f = self.update()

        f3 = open("scop_input.txt","w")
        f3.write(f)
        f3.close()

        if LOG>=100:
            print("scop input: \n")
            print(f)
            print("\n")
        if LOG:
            print("solving using parameters: \n ")
            print("  TimeLimit =%s second \n"%time)
            print("  RandomSeed= %s \n"%seed)
            print("  OutputFlag= %s \n"%LOG)

        import subprocess
        
        script = "./scop"
        
        if platform.system() == "Windows":
            cmd = "scop-win -time "+str(time)+" -seed "+str(seed) #solver call for win
        elif platform.system()== "Darwin":
            if platform.mac_ver()[2]=="arm64": #M1
                cmd = f"{script}-m1 -time "+str(time)+" -seed "+str(seed)
            else:
                cmd = f"{script}-mac -time "+str(time)+" -seed "+str(seed) #solver call for mac
        elif platform.system() == "Linux":
            cmd = f"{script}-linux -time "+str(time)+" -seed "+str(seed) #solver call for linux
            
        if self.Params.Initial:
            cmd += " -initsolfile scop_best_data.txt"

        try:
            if platform.system() == "Windows": #Winの場合にはコマンドをsplit!
                pipe = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
            else:
                pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
            print("\n ================ Now solving the problem ================ \n")
            
            out, err = pipe.communicate(f.encode()) #get the result
            if out ==b"":
                raise OSError
                
        except OSError:
            print("error: could not execute command")
            print("please check that the solver is in the path")
            self.Status = 7  #execution falied
            return None, None

        if err!=None:
            if int(sys.version_info[0])>=3:
                err = str(err, encoding='utf-8')
            f2 = open("scop_error.txt","w")
            f2.write(err)
            f2.close()

        if int(sys.version_info[0])>=3:
            out = str(out, encoding='utf-8')

        if LOG:
            print (out, '\n')
        #print ("out=",out)
        #print ("err=",err)
        #print("Return Code=",pipe.returncode)

        f = open("scop_out.txt","w")
        f.write(out)
        f.close()

        #check the return code
        self.Status = pipe.returncode
        if self.Status !=0: #if the return code is not "optimal", then return
            print("Status=",self.Status)
            print("Output=",out)
            return None, None

        #extract the solution and the violated constraints
        s0 = "[best solution]"
        s1 = "penalty"
        s2 = "[Violated constraints]"
        i0 = out.find(s0) + len(s0)
        i1 = out.find(s1, i0)
        i2 = out.find(s2, i1) + len(s2)

        data = out[i0:i1].strip()

        #save the best solution
        f3 = open("scop_best_data.txt","w")
        f3.write(data.lstrip())
        f3.close()

        sol = {}
        if data != "":
            for s in data.split("\n"):
                name, value = s.split(":")
                sol[name]=value.strip() #remove redunant string

        data = out[i2:].strip()
        violated = {}
        if data != "":
            for s in data.split("\n"):
                try:
                    name, value = s.split(":")
                except:
                    print("Error String=",s)

                try:
                    temp=int(value)
                except:
                    violated[name] = value
                else:
                    violated[name] = int(value)

        #set the optimal solution to the variable
        for name in sol:
            if name in self.varDict:
                self.varDict[name].value = sol[name]
            else:
                raise NameError("Solution {0} is not in variable list".format(name))

        #evaluate the left hand sides of the constraints
        for con in self.constraints:

            if isinstance(con,Linear):
                lhs=0
                for (coeff,var,domain) in con.terms:
                    if var.value==domain:
                        lhs+=coeff

                con.lhs=lhs
            if isinstance(con,Quadratic):
                lhs=0
                #print con.terms
                for (coeff,var1,domain1,var2,domain2) in con.terms:
                    if var1.value==domain1 and var2.value==domain2:
                        lhs+=coeff

                con.lhs=lhs
            if isinstance(con,Alldiff):
                VarSet=set([])
                lhs=0
                for v in con.variables:
                    index=v.domain.index(v.value)
                    #print v,index
                    if index in VarSet:
                        lhs+=1
                    VarSet.add(index)
                #print VarSet
                con.lhs=lhs
        #return dictionaries containing the solution and the violated constraints
        return sol,violated

#hide
#show_doc(Model)
#show_doc(Model.addVariable)
#show_doc(Model.addVariables)
#show_doc(Model.addConstraint)
#show_doc(Model.optimize)

if __name__ == '__main__':
    model = Model('test')
    model.addVariable(name="x[1]",domain=[0,1,2])
    print(model)
    model.Params.TimeLimit= 1
    sol, violated = model.optimize()
    print("solution=", sol)
    print("violated constraints=", violated)

#export
class Constraint(BaseModel):
    """
     Constraint base class
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: Optional[Any] = None
    weight: Any = 1

    ID: ClassVar[int] = 0

    @model_validator(mode='after')
    def init_constraint(self) -> 'Constraint':
        if self.name is None or self.name == "":
            self.name = f"__CON[{Constraint.ID}]"
            Constraint.ID += 1
        if not isinstance(self.name, str):
            raise ValueError("Constraint name must be a string")
        self.name = str(self.name).translate(_trans)
        self.weight = str(self.weight)
        return self

    def __init__(self, name=None, weight=1, **kwargs):
        super().__init__(name=name, weight=weight, **kwargs)

    def setWeight(self,weight):
        self.weight = str(weight)

#hide
#show_doc(Constraint)

#export
class Linear(Constraint):
    """
    Linear ( name, weight=1, rhs=0, direction="<=" )
    Linear constraint constructor.

    Arguments:
    - name: Name of linear constraint.
    - weight (optiona): Positive integer representing importance of constraint.
    - rhs: Right-hand-side constant of linear constraint.
    - direction: Rirection (or sense) of linear constraint; "<=" (default) or ">=" or "=".

    Attributes:
    - name: Name of linear constraint.
    - weight (optional): Positive integer representing importance of constraint.
    - rhs: Right-hand-side constant of linear constraint.
    - lhs: Left-hand-side constant of linear constraint.
    - direction: Direction (or sense) of linear constraint; "<=" (default) or ">=" or "=".
    - terms: List of terms in left-hand-side of constraint. Each term is a tuple of coeffcient,variable and its value.
    """
    rhs: int = 0
    direction: str = "<="
    terms: List[Tuple[Any, Any, Any]] = Field(default_factory=list)
    lhs: int = 0

    @model_validator(mode='after')
    def init_linear(self) -> 'Linear':
        if not isinstance(self.rhs, int):
            raise ValueError("Right-hand-side must be an integer.")
        if self.direction not in ["<=", ">=", "="]:
            raise NameError("direction setting error;direction should be one of '<=', '>=', or '='")
        return self

    def __init__(self, name=None, weight=1, rhs=0, direction="<=", **kwargs):
        """
        Constructor of linear constraint class:
        """
        super().__init__(name=name, weight=weight, rhs=rhs, direction=direction, **kwargs)

    def __str__(self):
        """ 
            return the information of the linear constraint
            the constraint is expanded and is shown in a readable format
        """
        f =["{0}: weight= {1} type=linear".format(self.name, self.weight)]
        for (coeff,var,value) in self.terms:
            f.append( "{0}({1},{2})".format(str(coeff),var.name,str(value)) )
        f.append( self.direction+str(self.rhs) +"\n" )
        return " ".join(f)

    def addTerms(self,coeffs=[],vars=[],values=[]):
        """
            - addTerms ( coeffs=[],vars=[],values=[] )
            Add new terms into left-hand-side of linear constraint.

            Arguments:
            - coeffs: Coefficients for new terms; either a list of coefficients or a single coefficient. The three arguments must have the same size.
            - vars: Variables for new terms; either a list of variables or a single variable. The three arguments must have the same size.
            - values: Values for new terms; either a list of values or a single value. The three arguments must have the same size.

            Example usage:

            L.addTerms(1, y, "A")
            L.addTerms([2, 3, 1], [y, y, z], ["C", "D", "C"]) #2 X[y,"C"]+3 X[y,"D"]+1 X[z,"C"]
        """
        if type(coeffs) !=type([]): #need a check whether coeffs is numeric ...
            #arguments are not a list; add a term
            if type(coeffs)==type(1):  #整数の場合だけ追加する．
                self.terms.append( (coeffs,vars,str(values)))
            else:
                raise ValueError("Coefficient must be an integer.")
        elif type(coeffs)!=type([]) or type(vars)!=type([]) or type(values)!=type([]):
            raise TypeError("coeffs, vars, values must be lists")
        elif len(coeffs)!=len(vars) or len(coeffs)!=len(values):
            raise TypeError("length of coeffs, vars, values must be identical")
        else:
            for i in range(len(coeffs)):
                self.terms.append( (coeffs[i],vars[i],str(values[i])))

    def setRhs(self,rhs=0):
        if type(rhs) != type(1):
            raise ValueError("Right-hand-side must be an integer.")
        else:
            self.rhs = rhs

    def setDirection(self,direction="<="):
        if direction in ["<=",">=","="]:
            self.direction = direction
        else:
            raise NameError(
                "direction setting error; direction should be one of '<=', '>=', or '='"
                           )

    def feasible(self,allvars):
        """ 
        return True if the constraint is defined correctly
        """
        for (coeff,var,value) in self.terms:
            if var.name not in allvars:
                raise NameError("no variable in the problem instance named %r" % var.name)
            if value not in allvars[var.name].domain:
                raise NameError("no value %r for the variable named %r" % (value, var.name))
        return True

#hide
#show_doc(Linear)
#show_doc(Linear.addTerms)

# 通常の制約
L = Linear(name = "a linear constraint", rhs = 10, direction = "<=" )
x = Variable(name="x", domain=["A","B","C"] )
L.addTerms(3, x, "A")
print(L)

#右辺定数や制約の係数が整数でない場合
try:
    L = Linear(name = "a linear constraint", rhs = 10.56, direction = "=" )
except ValueError as error:
    print(error)
    
x = Variable(name="x", domain=["A","B","C"] )
try:
    L.addTerms(3.1415, x, "A")
except ValueError as error:
    print(error)

#export
class Quadratic(Constraint):
    """
    Quadratic ( name, weight=1, rhs=0, direction="<=" )
    Quadratic constraint constructor.

    Arguments:
    - name: Name of quadratic constraint.
    - weight (optional): Positive integer representing importance of constraint.
    - rhs: Right-hand-side constant of linear constraint.
    - direction: Direction (or sense) of linear constraint; "<=" (default) or ">=" or "=".

    Attributes:
    - name: Name of quadratic constraint.
    - weight (optiona): Positive integer representing importance of constraint.
    - rhs: Right-hand-side constant of linear constraint.
    - lhs: Left-hand-side constant of linear constraint.
    - direction: Direction (or sense) of linear constraint; "<=" (default) or ">=" or "=".
    - terms: List of terms in left-hand-side of constraint. Each term is a tuple of coeffcient, variable1, value1, variable2 and value2.
    """

    rhs: int = 0
    direction: str = "<="
    terms: List[Tuple[Any, Any, Any, Any, Any]] = Field(default_factory=list)
    lhs: int = 0

    @model_validator(mode='after')
    def init_quadratic(self) -> 'Quadratic':
        if not isinstance(self.rhs, int):
            raise ValueError("Right-hand-side must be an integer.")
        if self.direction not in ["<=", ">=", "="]:
            raise NameError("direction setting error;direction should be one of '<=', '>=', or '='")
        return self

    def __init__(self, name=None, weight=1, rhs=0, direction="<=", **kwargs):
        super().__init__(name=name, weight=weight, rhs=rhs, direction=direction, **kwargs)

    def __str__(self):
        """ return the information of the quadratic constraint
            the constraint is expanded and is shown in a readable format
        """
        f = [ "{0}: weight={1} type=quadratic".format(self.name,self.weight) ]
        for (coeff,var1,value1,var2,value2) in self.terms:
            f.append( "{0}({1},{2})({3},{4})".format(
                str(coeff),var1.name,str(value1),var2.name,str(value2)
                ))
        f.append( self.direction+str(self.rhs) +"\n" )
        return " ".join(f)

    def addTerms(self,coeffs=[],vars=[],values=[],vars2=[],values2=[]):
        """
        addTerms ( coeffs=[],vars=[],values=[],vars2=[],values2=[])

        Add new terms into left-hand-side of qua
        dratic constraint.

        Arguments:
        - coeffs: Coefficients for new terms; either a list of coefficients or a single coefficient. The five arguments must have the same size.
        - vars: Variables for new terms; either a list of variables or a single variable. The five arguments must have the same size.
        - values: Values for new terms; either a list of values or a single value. The five arguments must have the same size.
        - vars2: Variables for new terms; either a list of variables or a single variable. The five arguments must have the same size.
        - values2: Values for new terms; either a list of values or a single value. The five arguments must have the same size.

        Example usage:

        L.addTerms(1.0, y, "A", z, "B")

        L.addTerms([2, 3, 1], [y, y, z], ["C", "D", "C"], [x, x, y], ["A", "B", "C"])
                  #2 X[y,"C"] X[x,"A"]+3 X[y,"D"] X[x,"B"]+1 X[z,"C"] X[y,"C"]

        """
        if type(coeffs) !=type([]): 
            if type(coeffs)==type(1):  #整数の場合だけ追加する．
                self.terms.append( (coeffs,vars,str(values),vars2,str(values2)))
            else:
                raise ValueError("Coefficient must be an integer.")
        elif type(coeffs)!=type([]) or type(vars)!=type([]) or type(values)!=type([]) \
             or type(vars2)!=type([]) or type(values2)!=type([]):
            raise TypeError("coeffs, vars, values must be lists")
        elif len(coeffs)!=len(vars) or len(coeffs)!=len(values) or len(values)!=len(vars) \
             or len(coeffs)!=len(vars2) or len(coeffs)!=len(values2):
            raise TypeError("length of coeffs, vars, values must be identical")
        else:
            for i in range(len(coeffs)):
                self.terms.append( (coeffs[i],vars[i],str(values[i]),vars2[i],str(values2[i])))

    def setRhs(self,rhs=0):
        if type(rhs) != type(1):
            raise ValueError("Right-hand-side must be an integer.")
        else:
            self.rhs = rhs

    def setDirection(self,direction="<="):
        if direction in ["<=", ">=", "="]:
            self.direction = direction
        else:
            raise NameError(
                "direction setting error;direction should be one of '<=', '>=', or '='"
                  )

    def feasible(self,allvars):
        """
          return True if the constraint is defined correctly
        """
        for (coeff,var1,value1,var2,value2) in self.terms:
            if var1.name not in allvars:
                raise NameError("no variable in the problem instance named %r" % var1.name)
            if var2.name not in allvars:
                raise NameError("no variable in the problem instance named %r" % var2.name)
            if value1 not in allvars[var1.name].domain:
                raise NameError("no value %r for the variable named %r" % (value1, var1.name))
            if value2 not in allvars[var2.name].domain:
                raise NameError("no value %r for the variable named %r" % (value2, var2.name))
        return True

#hide
#show_doc(Quadratic)
#show_doc(Quadratic.addTerms)

Q = Quadratic(name = "a quadratic constraint", rhs = 10, direction = "<=" )
x = Variable(name="x",domain=["A","B","C"] )
y = Variable(name="y",domain=["A","B","C"] )
Q.addTerms([3,9], [x,x], ["A","B"], [y,y], ["B","C"])
print(Q)

#export
class Alldiff(Constraint):
    """
    Alldiff ( name=None,varlist=None,weight=1 )
    Alldiff type constraint constructor.

    Arguments:
    - name: Name of all-different type constraint.
    - varlist (optional): List of variables that must have differennt value indices.
    - weight (optional): Positive integer representing importance of constraint.

    Attributes:
    - name: Name of all-different type  constraint.
    - varlist (optional): List of variables that must have differennt value indices.
    - lhs: Left-hand-side constant of linear constraint.

    - weight (optional): Positive integer representing importance of constraint.
    """
    varlist: Optional[List[Variable]] = None
    lhs: int = 0
    variables: Set[Variable] = Field(default_factory=set)

    @model_validator(mode='after')
    def init_alldiff(self) -> 'Alldiff':
        if self.varlist is None:
            self.variables = set()
        else:
            for var in self.varlist:
                if not isinstance(var, Variable):
                    raise NameError("error: %r should be a subclass of Variable" % var)
            self.variables = set(self.varlist)
        return self

    def __init__(self, name=None, varlist=None, weight=1, **kwargs):
        #call the super class (Constraint) to initialize Alldiff
        super().__init__(name=name, varlist=varlist, weight=weight, **kwargs)

    def __str__(self):
        """
        return the information of the alldiff constraint
        """
        f = [ "{0}: weight= {1} type=alldiff ".format(self.name,self.weight) ]
        for var in self.variables:
            f.append( var.name )
        f.append( "; \n" )
        return " ".join(f)

    def addVariable(self,var):
        """
        addVariable ( var )
        Add new variable into all-different type constraint.

        Arguments:
        - var: Variable object added to all-different type constraint.

        Example usage:

        AD.addVaeiable( x )

        """
        if not isinstance(var,Variable):
            raise NameError("error: %r should be a subclass of Variable" % var)

        if var in self.variables:
            print("duplicate variable name error when adding variable %r" % var)
            return False
        self.variables.add(var)

    def addVariables(self, varlist):
        """
        addVariables ( varlist )
        Add variables into all-different type constraint.

        Arguments:
        - varlist: List or tuple of variable objects added to all-different type constraint.

        Example usage:

        AD.addVariables( x, y, z )

        AD.addVariables( [x1,x2,x2] )

        """
        for var in varlist:
            self.addVariable(var)

    def feasible(self,allvars):
        """
           return True if the constraint is defined correctly
        """
        for var in self.variables:
            if var.name not in allvars:
                raise NameError("no variable in the problem instance named %r" % var.name)
        return True

#hide
#show_doc(Alldiff)
#show_doc(Alldiff.addVariable)
#show_doc(Alldiff.addVariables)

A = Alldiff(name="a alldiff constraint")
x = Variable(name="x",domain=["A","B","C"] )
y = Variable(name="y",domain=["A","B","C"] )
A.addVariables([x,y])
print(A)

'''
Example 1 (Assignment Problem):
Three jobs (0,1,2) must be assigned to three workers (A,B,C)
so that each job is assigned to exactly one worker.
The cost matrix is represented by the list of lists
Cost=[[15, 20, 30],
      [7, 15, 12],
      [25,10,13]],
where rows of the matrix are workers, and columns are jobs.
Find the minimum cost assignment of workers to jobs.
'''

if __name__ == '__main__':
    workers=['A','B','C']
    Jobs   =[0,1,2]
    Cost={ ('A',0):15, ('A',1):20, ('A',2):30,
           ('B',0): 7, ('B',1):15, ('B',2):12,
           ('C',0):25, ('C',1):10, ('C',2):13 }

    m=Model()
    x={}
    for i in workers:
        x[i]=m.addVariable(name=i,domain=Jobs)

    xlist=[]
    for i in x:
        xlist.append(x[i])

    con1=Alldiff('AD',xlist,weight='inf')

    con2=Linear('linear_constraint',weight=1,rhs=0,direction='<=')
    for i in workers:
        for j in Jobs:
            con2.addTerms(Cost[i,j],x[i],j)

    m.addConstraint(con1)
    m.addConstraint(con2)

    print(m)

    m.Params.TimeLimit=1
    sol,violated=m.optimize()

    if m.Status==0:
        print('solution')
        for x in sol:
            print (x,sol[x])
        print ('violated constraint(s)')
        for v in violated:
            print (v,violated[v])


"""
Example 2 (Generalized Assignment Problem):
Three jobs (0,1,2) must be assigned to five workers (A,B,C,D,E).
The numbers of workers that must be assigned to jobs 0,1 and 2 are 1,1 and 2, respectively. 
The cost matrix is represented by the list of lists  
Cost=[[15, 20, 30],
[7, 15, 12],
[25,10,13],
[15,18,3],
[5,12,17]]
where rows are workers, and columns are jobs.
Find the minimum cost assignment of workers to jobs.
"""

if __name__ == '__main__':
    m=Model()
    workers=['A','B','C','D','E']
    Jobs   =[0,1,2]
    Cost={ ('A',0):15, ('A',1):20, ('A',2):30,
           ('B',0): 7, ('B',1):15, ('B',2):12,
           ('C',0):25, ('C',1):10, ('C',2):13,
           ('D',0):15, ('D',1):18, ('D',2): 3,
           ('E',0): 5, ('E',1):12, ('E',2):17
           }
    LB={0: 1,
        1: 2,
        2: 2
        }
    x={}
    for i in workers:
        x[i]=m.addVariable(name=i,domain=Jobs)
    LBC={} #dictionary for keeping lower bound constraints
    for j in Jobs:
        LBC[j]=Linear('LB{0}'.format(j),'inf',LB[j],'>=')
        for i in workers:
            LBC[j].addTerms(1,x[i],j)
        m.addConstraint(LBC[j])
    obj=Linear('obj')
    for i in workers:
        for j in [0,1,2]:
            obj.addTerms(Cost[i,j],x[i],j)
    m.addConstraint(obj)
    m.Params.TimeLimit=1
    sol,violated=m.optimize()
    print(m)

    if m.Status==0:
        print('solution')
        for x in sol:
            print (x,sol[x])
        print ('violated constraint(s)')
        for v in violated:
            print (v,violated[v])

"""
Example 3 (Variation of Generalized Assignment Problem):
Three jobs (0,1,2) must be assigned to five workers (A,B,C,D,E).
The minimum numbers of workers that must be assigned to jobs 0,1 and 2 are 1,2 and 2, respectively.
This lower bound is represented by a dictionary:
LB={0: 1,
    1: 2,
    2: 2
    }
where keys are jobs and values are lower bounds.
The cost matrix is represented by a dictionary:
Cost={ ("A",0):15, ("A",1):20, ("A",2):30,
       ("B",0): 7, ("B",1):15, ("B",2):12,
       ("C",0):25, ("C",1):10, ("C",2):13,
       ("D",0):15, ("D",1):18, ("D",2): 3,
       ("E",0): 5, ("E",1):12, ("E",2):17
       }
where keys are tuples of workers and jobs, and values are costs.
We add an additional condition: worker A cannot do the job with worker C.
Find the minimum cost assignment of workers to jobs.
"""

if __name__ == '__main__':
    m=Model()
    workers=["A","B","C","D","E"]
    Jobs   =[0,1,2]
    Cost={ ("A",0):15, ("A",1):20, ("A",2):30,
           ("B",0): 7, ("B",1):15, ("B",2):12,
           ("C",0):25, ("C",1):10, ("C",2):13,
           ("D",0):15, ("D",1):18, ("D",2): 3,
           ("E",0): 5, ("E",1):12, ("E",2):17
           }
    LB={0: 1,
        1: 2,
        2: 2
        }
    x={}
    for i in workers:
        x[i]= m.addVariable(i,Jobs)
    LBC={}
    for j in Jobs:
        LBC[j]=Linear("LB{0}".format(j),"inf",LB[j],">=")
        for i in workers:
            LBC[j].addTerms(1,x[i],j)
        m.addConstraint(LBC[j])
    obj=Linear("obj",1,0,"<=")
    for i in workers:
        for j in Jobs:
            obj.addTerms(Cost[i,j],x[i],j)
    m.addConstraint(obj)
    conf=Quadratic("conflict",100,0,"=")
    for j in Jobs:
        conf.addTerms(1,x["A"],j,x["C"],j)
    m.addConstraint(conf)
    m.Params.TimeLimit=1
    sol,violated= m.optimize()
    print (m)
    if m.Status==0:
        print ("solution")
        for x in sol:
            print (x,sol[x])
        for v in violated:
            print (v,violated[v])
