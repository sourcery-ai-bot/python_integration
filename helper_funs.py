'''
Helper functions.

'''
import os
import re
import numpy as np

def removeModelFiles():
	"""
	Removes all files generated by the CVODE solver.

	"""
	# check if bin directory exists
	if os.path.exists('bin'):
		for binfile in os.listdir('./bin'):
			os.remove(f'./bin/{binfile}')
		os.rmdir('bin')
	if os.path.exists('includes'):
		for includesfile in os.listdir('./includes'):
			os.remove(f'./includes/{includesfile}')
		os.rmdir('includes')
	if os.path.exists('src'):
		for cfile in os.listdir('./src'):
			if cfile not in ['integrate_cvode.c', 'integrate_idas.c']:
				os.remove(f'./src/{cfile}')

	return 1


def cleanModelName(model_dict):
	"""
	cleans up the module name.
	"""

	model_name = model_dict['name']
	model_name = model_name.replace(' ','_')
	model_name = model_name.replace('-','_')
	model_name = model_name.replace('+','_')
	model_name = model_name.replace('/','_')
	model_name = model_name.replace('\\','_')
	model_name = model_name.replace('__','_')
	model_name = model_name.replace('__','_')
	model_name = model_name.replace('__','_')

	short_name = ''
	# limit short name to 20 characters
	for part in model_name.split('_'):
		short_name = f'{short_name}_{part}'
		if len(short_name) > 20:
			break

	return short_name[1:]
	

def findAndReplace(pattern, dest_str, repl_str):
	"""
	replace string in _document
	Written by Thomas Spiesser

	pattern : string (will be substituted)
	dest_str : string (with pattern in it)
	repl_str : string (substitute)

	returns : dest_str with replaced string
	"""
	# not followed by alphanumeric [a-zA-Z0-9_] or (|) is at end of string ($)
	re_comp = re.compile(r'%s(?=\W|$)' % (pattern))
	# substitute pattern with repl_str in dest_str if found
	return re_comp.sub(repl_str, dest_str)


def cleanFormula(formula):
	"""
	clean text format of SBML file
	Written by Thomas Spiesser

	formula : string (SBML file)
	returns cleaned formula
	"""
	#  spaces around special characters
	for s in ['(', ')', '*', '/', '+', '-', ',']:
		formula = formula.replace(s, f' {s} ')
	# reduce spaces '   ' -> ' '
	for _ in range(3):
		formula = formula.replace("  ", " ")
	if match := re.search(r'\de - ', formula):
		my_digit = match[0][0]
		formula = formula.replace(match[0], f'{my_digit}e-')
	# convert string to float with decimal point and back ('1' to '1.0')
	split_formula = formula.split(' ')
	n_split_formula = []
	for i in split_formula:
		try:
			i = float(i)
			i = str(i)
			n_split_formula.append(i)
		except:
			n_split_formula.append(i)
	formula = ' '.join(n_split_formula)
	# return cleaned formula
	return formula


def convToCstr(formula):
	"""
	convert sympy expression to c-code

	"""

	from sympy import ccode
	
	formula_c = []
	for i in range(len(formula[:])):
		c_str = ccode(formula[i])
		# remove Heaviside warning
		c_str = c_str.replace("// Not supported in C:\n// Heaviside\n", '')
		formula_c.append(c_str)

	return formula_c


def modelHash(model_dict):
	"""
	generate checksum for model dict
	"""

	model_structure = [model_dict[m] for m in model_dict if m not in ['initpars','initvars']]
	#checksum = abs(reduce(lambda x,y : x^y, [hash(str(item)) for item in model_dict.items()]))

	return abs(hash(repr(model_structure)))


def SBMLwritePythonModule(module_dict,doc_txt=''):
	"""
	Transforms a given model dictionary from SBML to a python script. Optionally, a docstring for the python file can be passed.
	"""
	import sympy as sym

	# dictionary for python script sections
	sections = {'name':'Model Name',
				'vars':'Model Species',
				'pars':'Model Parameters',
				'initvars':'Initial Values for Species',
				'initpars':'Initial Values for Parameters'}

	additional_sections = {'units':'Species Units',
						   'state':'Species States',
						   'sp_annotations':'Species Annotations',
						   'sp_compartment':'Species Compartment',
						   'sp_names':'Species Names',
						   'com_annotations':'Compartment Annotations'}

	# open new python script
	g = open('./python_models/%s.py' % cleanModelName(module_dict),'w')

	# write function header
	g.write('\ndef %s():' % cleanModelName(module_dict))
	# write docstring
	docstring ="\n\t'''\n\t%s\n\t'''" % doc_txt
	g.write(docstring+'\n')

	# write module dicitonary
	g.write('\tmodule_dict = {}')
	for d in sections:
		g.write("\n\n\t### %s:\n" % sections[d])
		if d == 'name':
			txt = "\tmodule_dict['%s'] = '%s'\n" % (d, module_dict[d])
		else:
			txt = "\tmodule_dict['%s'] = %s\n" % (d, module_dict[d])
		txt = findAndReplace(",",txt,",\n\t\t\t\t\t\t")
		g.write(txt)

	# write additional sections
	for d in additional_sections:
		if d in module_dict:
			g.write("\n\n\t### %s:\n" % additional_sections[d])
			if d == 'name':
				txt = "\tmodule_dict['%s'] = '%s'\n" % (d, module_dict[d])
			else:
				txt = "\tmodule_dict['%s'] = %s\n" % (d, module_dict[d])
			# txt = txt.replace(',',',\n\t\t\t\t\t\t')
			txt = findAndReplace(",",txt,",\n\t\t\t\t\t\t")
			g.write(txt)
		else:
			print "\n%s is not defined in model dictionary! Skipping..." % (d)


	# get ode species list
	ode_species = [var for var in module_dict['vars'] if var in module_dict['odes']]
		
	# write reactions dict
	if 'reactions' in module_dict: 
		# get reactions list
		reactions = [reac for reac in module_dict['reacs'] if reac in module_dict['reactions']]

		g.write("\n\n\t### Reactions:\n")
		g.write("\treactions = {}\n")
		for reac_id in reactions:
			g.write("\treactions['%s'] = {'rate': {}, 'products': {}, 'substrates': {}, 'modifiers': {}}\n" % reac_id)

		# write rates
		g.write("\n\n\t### Rates:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % module_dict['reaction_names'][reac_id])
			# write reaction rate
			g.write("\treactions['%s']['rate'] = '%s'\n" % (reac_id, module_dict['reactions'][reac_id]['rate']))  

		# write substrates
		g.write("\n\n\t### Substrates:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % module_dict['reaction_names'][reac_id])
			# write reaction substrates
			g.write("\treactions['%s']['substrates'] = %s\n" % (reac_id, module_dict['reactions'][reac_id]['substrates']))  

		# write products
		g.write("\n\n\t### Products:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % module_dict['reaction_names'][reac_id])
			# write reaction products
			g.write("\treactions['%s']['products'] = %s\n" % (reac_id, module_dict['reactions'][reac_id]['products'])) 
		
		# write modifiers
		g.write("\n\n\t### Modifiers:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % module_dict['reaction_names'][reac_id])
			# write reaction modifiers
			g.write("\treactions['%s']['modifiers'] = %s\n" % (reac_id, module_dict['reactions'][reac_id]['modifiers'])) 

		g.write("\n\tmodule_dict['reactions'] = reactions")
		
		# create symbolic flux vector out of reaction ids
		rate_list = {reac_id:"reactions['%s']['rate']" % (reac_id) for reac_id in reactions}
		v = sym.Matrix(sym.symbols(reactions))
		v = np.array(v).flatten()

		# get stoichiometric matrix
		N = module_dict['N']
		# get symbolic odes depending on fluxes v_*
		xdot = np.dot(N,v)
		# convert xdot matrix to list of strings
		xdot_list = [str(f) for f in xdot.tolist()]
		# replace reaction ids by dict values
		for reac_id in reactions:
			xdot_list = [findAndReplace(reac_id,f,rate_list[reac_id]) for f in xdot_list]

		# write ode header
		g.write("\n\n\t### ODEs\n\todes = {}\n")

		# search pattern for making strings out of the stoichiometric coeffs.
		pattern = "(\-?[0-9]+\.[0-9]*(e-?[0-9]+)?)"

		# convert odes to string with fluxes
		for xi,var in enumerate(ode_species):
			# get species name for doc string
			species_name = module_dict['sp_names'][var]
			# get string for ode xdot array
			txt = xdot_list[xi]
			# replace stoichiometric coeffs by strings
			re_comp = re.compile(pattern)
			txt = re_comp.sub("'\g<1>'",txt)
			# replace + by string
			txt = txt.replace(' + ',' + \' + \' + ')
			# replace - by string
			txt = txt.replace(' - ',' + \' - \' + ')
			# replace * by string
			txt = txt.replace('*',' + \' * \' + ')

			if txt == '0':
				txt = "'0'"
			# add left hand side of ode
			txt = "\todes['%s'] = %s\n" % (var, txt)
			# write to python script
			g.write("\t# %s\n" % species_name)
			g.write(txt)

		g.write("\n\tmodule_dict['odes'] = odes")    

	else:
		# write ode header
		g.write("\n\n\t### ODEs\n\todes = {}\n")

		for var in ode_species:
			if 'species_name' in module_dict.keys():
				# get species name for doc string   
				species_name = module_dict['sp_names'][var]
				g.write("\t# %s\n" % species_name)
			
			txt = "\todes['%s'] = '%s'\n" % (var, module_dict['odes'][var])            
			g.write(txt)

		g.write("\n\tmodule_dict['odes'] = odes")  

		print "\nNo reactions specified in model dictionary! Using ODEs instead."

	# write return command
	g.write("\n\n\treturn module_dict\n")
	# close file
	g.close()

	print "\n Python module \"%s\" successfully written!" % cleanModelName(module_dict)

def writePythonModule(module_dict, doc_txt=''):
	"""
	Transforms a given model dictionary to a python script. Optionally, a docstring for the python file can be passed.
	"""
	# dictionary for python script sections
	sections = {'name':'Model Name',
				'vars':'Model Species',
				'pars':'Model Parameters',
				'initvars':'Initial Values for Species',
				'initpars':'Initial Values for Parameters'}

	additional_sections = {'units':'Species Units',
						   'sp_annotations':'Species Annotations',
						   'sp_compartment':'Species Compartment',
						   'com_annotations':'Compartment Annotations',
						   'sp_states': 'States'}

	# open new python script
	with open("./python_models/%s.py" % cleanModelName(module_dict),"w") as g:
		#g = open('./python_models/%s.py' % cleanModelName(module_dict),'w')

		# write function header
		g.write('\ndef %s():' % cleanModelName(module_dict))
		# write docstring
		docstring ="\n\t'''\n\t%s\n\t'''" % doc_txt
		g.write(docstring+'\n')

		# write module dicitonary
		g.write('\tmodule_dict = {}')
		for d in sections:
			g.write("\n\n\t### %s:\n" % sections[d])
			if d == 'name':
				txt = "\tmodule_dict['%s'] = '%s'\n" % (d, module_dict[d])
			else:
				txt = "\tmodule_dict['%s'] = %s\n" % (d, module_dict[d])
			txt = findAndReplace(",",txt,",\n\t\t\t\t\t\t")
			g.write(txt)

		
		# write additional sections
		for d in additional_sections:
			if d in module_dict:
				g.write("\n\n\t### %s:\n" % additional_sections[d])
				if d == 'name':
					txt = "\tmodule_dict['%s'] = '%s'\n" % (d, module_dict[d])
				else:
					txt = "\tmodule_dict['%s'] = %s\n" % (d, module_dict[d])
				# txt = txt.replace(',',',\n\t\t\t\t\t\t')
				txt = findAndReplace(",",txt,",\n\t\t\t\t\t\t")
				g.write(txt)
			else:
				print "\n%s is not defined in model dictionary! Skipping..." % (d)

		
		# get ode species list
		ode_species = [var for var in module_dict['vars'] if var in module_dict['odes']]

		# get algebraic equation list
		alg_species = [var for var in module_dict['vars'] if var in module_dict['alg_eqs']]
			
		# get reactions list
		reactions = [reac for reac in module_dict['reactions']]

		g.write("\n\n\t### Reactions:\n")
		g.write("\treactions = {}\n")
		for reac_id in reactions:
			g.write("\treactions['%s'] = {'rate': {}, 'products': {}, 'substrates': {}, 'modifiers': {}}\n" % reac_id)

		# write rates
		g.write("\n\n\t### Rates:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % reac_id)
			# write reaction rate
			g.write("\treactions['%s']['rate'] = '%s'\n" % (reac_id, module_dict['reactions'][reac_id]['rate']))  

		# write substrates
		g.write("\n\n\t### Substrates:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % reac_id)
			# write reaction substrates
			g.write("\treactions['%s']['substrates'] = %s\n" % (reac_id, module_dict['reactions'][reac_id]['substrates']))  

		# write products
		g.write("\n\n\t### Products:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % reac_id)
			# write reaction products
			g.write("\treactions['%s']['products'] = %s\n" % (reac_id, module_dict['reactions'][reac_id]['products'])) 
		
		# write modifiers
		g.write("\n\n\t### Modifiers:\n")
		for reac_id in reactions:
			# write reaction name
			g.write("\t# %s\n" % reac_id)
			# write reaction modifiers
			g.write("\treactions['%s']['modifiers'] = %s\n" % (reac_id, module_dict['reactions'][reac_id]['modifiers'])) 

		g.write("\n\tmodule_dict['reactions'] = reactions")
		
		# create symbolic flux vector out of reaction ids
		rate_list = {reac_id:"reactions['%s']['rate']" % (reac_id) for reac_id in reactions}
		
		# write ode header
		g.write("\n\n\t### ODEs\n\todes = {}\n")

		# convert odes to string with fluxes
		for var in ode_species:
			txt = module_dict['odes'][var]
			# add left hand side of ode
			txt = "\todes['%s'] = '%s'\n" % (var, txt)
			# write to python script
			g.write("\t# %s\n" % var)
			g.write(txt)

		g.write("\n\tmodule_dict['odes'] = odes")    

		# write ode header
		g.write("\n\n\t### algebraic equations \n\talg_eqs = {}\n")

		# convert odes to string with fluxes
		for var in alg_species:
			txt = module_dict['alg_eqs'][var]
			# add left hand side of ode
			txt = "\talg_eqs['%s'] = '%s'\n" % (var, txt)
			# write to python script
			g.write("\t# %s\n" % var)
			g.write(txt)

			g.write("\n\tmodule_dict['alg_eqs'] = alg_eqs") 

		# write return command
		g.write("\n\n\treturn module_dict\n")
		# close file
		g.close()

		print "\n Python module \"%s\" successfully written!" % cleanModelName(module_dict)


def convToDict(model_name,x_names,p_names,dxdt,x0=[],p0=[]):
	"""
	converts lists of variables, parameters and odes to model dictionary
	"""
	model_dict = {
		'name': model_name,
		'odes': dict(zip(x_names, dxdt)),
		'vars': x_names,
		'pars': p_names,
		'initvars': dict(zip(x_names, 0.1 * np.ones([len(x_names)])))
		if x0 == []
		else dict(zip(x_names, x0)),
	}

	if p0 == []:
		model_dict['initpars'] = dict(zip(p_names, 0.1*np.ones([len(p_names)])))
	else:
		model_dict['initpars'] = dict(zip(p_names, p0))

	return model_dict


def plotVars(t, x, model_dict):
	'''
	plot trajectories
	'''

	from matplotlib import pyplot

	ode_species = model_dict['vars']
	name = model_dict['name']

	pyplot.plot(t, x)
	pyplot.legend(ode_species)
	pyplot.title(name)
	pyplot.xlabel('time [s]')
	pyplot.ylabel('concentrations [mM]')
	pyplot.show()


def plotVarsExp(t, x, tExp, data, model_dict):
	'''
	plot trajectories
	'''

	from matplotlib import pyplot

	ode_species = model_dict['vars']
	name = model_dict['name']

	pyplot.plot(t, x)
	pyplot.plot(tExp,data['x'],'x')
	pyplot.legend(ode_species)
	pyplot.title(name)
	pyplot.xlabel('time [s]')
	pyplot.ylabel('concentrations [mM]')
	pyplot.xlim([-0.05*t[-1],1.05*t[-1]])
	pyplot.show()


def mathToMatlab(math_str):

	import re

	# replace pow(a,b) by (a)^(b)
	pattern = "pow\s?\(\s?([A-Z_a-z0-9\s/]*),\s?([A-Z_a-z0-9\s/]*)\)"
	repl = "(\g<1>)^(\g<2>)"
	matlab_str = math_str.replace(' ','')
	matlab_str = re.sub(pattern, repl, matlab_str)

	# replace a**b by a^b
	matlab_str = matlab_str.replace('**','^')

	return matlab_str
