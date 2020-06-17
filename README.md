# blender_neptools
<p>A set of Blender tools to Import and Export to the Neptunia Games
<p><b>Use the ZIP file</b> to quickly install to Blender.
  <br>No need to unzip it.
  <br>Navigate to 'Edit > Preferences > Add-ons'. Use the install button here.

<p>Currently I have importing models working for:
<ul>
<li>Hyperdimension Neptunia Re;Birth1
<li>Hyperdimension Neptunia Re;Birth2
<li>Hyperdimension Neptunia Re;Birth3
<li>Megadimension Neptunia VII
</ul>

<p>Some face textures will fail. I assume it has to do with the way the faces are animated.

<p>I am quite familiar with Java but I am very new to Python.
<p>Blender add-ons are written in Python so I had to learn.


<h1>Importing from ISM2</h1>
Blender Menus -> 'File > Import > Neptunia Models (.ism2)'
<h2>CREDIT</h2>
<b>Random Talking Brush, howie</b>
<br>This script was written by me (LilacDogoo) based on a 3ds Max script written by Random Talking Bush.
<br>The 3ds Max script written by Random Talking Bush is based on the LightWave importer by howfie.
<br>If you use it, consider giving thanks to Idea Factory, Compile Heart, howfie, Random Talking Bush, and myself.


<h2>REMEMBER</h2>
I did not automate this completely, as of yet.
<p>You must do this yourself:
<ul>
<li>extract 'pac' file collections
<li>extract 'cl3' file collections
<li>convert 'tid' files to 'png' files
</ul>
<p>Blender should do the rest from there.
<p>Some links to help you:
<ul>
<li>Hyperdimension Neptunia Re;Birth 1 & 2  >  https://steamcommunity.com/sharedfiles/filedetails/?id=453717187
<li>Megadimension Neptunia Victory II  >  https://github.com/MysteryDash/Dash.FileFormats
</ul>

<h2>About the Face Problems</h2>
The more advanced characteres have a combination of textures to create the face. I did not get around to creating face assembly script yet.
<br>The UV's are there. So; assigning the face texture and transforming the UV's to fit should be easy to do manually.


<h1>Extracting ARC files</h1>
Currently only tested against 'Megadimension Neptunia VII' arc files. May work with other arc files.

<h2>How to use</h2>
<ol>
<li>Blender Menus -> 'NepTools > Generate VII DLC Descriptions'.
  <br>This creates a, more easy to scan through, list of you DLCs.
<li>Use the Text Editor within blender to view the 'DLC_descriptions.txt' that was created.
<li>Search for 'swim' to find all the swimsuit models. (Example)
<li>In this case we can see that 'Uzume Swimsuit Set' is listed under 'DLC000000000009500000'
<li>Blender Menus -> 'NepTools > Extract Arc File' (locate 'DLC000000000009500000').
  <br>A folder was created with the same name and location of the arc file.
<li>Blender Menus -> 'NepTools > ISM2 Importer (Neptunia)' (locate the ISM2 file within the extracted files).

<b>REMEMBER</b> I did not automate this completely as of yet. You must convert 'tid's to 'png's yourself.
    After that Blender will find them and apply them to your model for you.
