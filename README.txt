To wrap an Ansys model, there are three required steps.

1) Manually load the model in Ansys, and use the component manager to create and name the components that OpenMDAO will eventually use.  The most useful will be surfaces and node lists.  Give the components meaningful names, since those will be part of the variable names in the wrapper.

2) Run the wrapper generator.  It needs to know the path to the model, the model name, Ansys version, and the name of the wrapper.  

3) The generator will create a Python file with an instance-specific OpenMDAO Component for your model.  There will be input and output variables corresponding to all of the Ansys components you made in step 1.



