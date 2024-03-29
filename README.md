# SCOP Trial 
> SCOP (SOlver for Constraint Programming) trial 


## How to Install to Jupyter Notebook (Labo) and/or Google Colaboratory

1. Clone from github:
> `https://github.com/scmopt/scop.git`

2. Move to scoptrial directry (if you run scop from Jupyter, you need not to move to scop directory):
> `cd scop/scoptrial`

3. Change mode of execution file

 - for linux (e.g., Google Colab.)  
 > `!chmod +x scop-linux`   

 - for Mac intel 
 > `!chmod +x scop-mac`

 - for Mac sillicone (Mx series) 
 > `!chmod +x scop-m1`  

4. Import package and write a code:> `from scop import *`
5. (Option) Install other packages if necessarily: 

> `!pip install plotly pandas numpy metplotlib`

## How to use

See https://scmopt.github.io/manual/14scop.html  and  https://www.logopt.com/scop2/ 

Here is an example (after moving scop/scoptrial directory). 

```python
from scop import *
```

```python
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
```

    Model: 
    number of variables = 3  
    number of constraints= 2  
    variable A:['0', '1', '2'] = None 
    variable B:['0', '1', '2'] = None 
    variable C:['0', '1', '2'] = None 
    AD: weight= inf type=alldiff  A B C ;  :LHS =0  
    linear_constraint: weight= 1 type=linear 15(A,0) 20(A,1) 30(A,2) 7(B,0) 15(B,1) 12(B,2) 25(C,0) 10(C,1) 13(C,2) <=0 :LHS =0 
    
     ================ Now solving the problem ================ 
    
    solution
    A 0
    B 2
    C 1
    violated constraint(s)
    linear_constraint 37

