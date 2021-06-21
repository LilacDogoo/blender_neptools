# blender_neptools
<p>A set of Blender tools to Import and Export to the Neptunia Games
<p><b>Use the ZIP file</b> to quickly install to Blender.
  <br>No need to unzip it.
  <br>Navigate to 'Edit > Preferences > Add-ons'. Use the install button here.

<h2>Supported games</h2
<ul>
<li>Hyperdimension Neptunia Re;Birth1
<li>Hyperdimension Neptunia Re;Birth2
<li>Hyperdimension Neptunia Re;Birth3
<li>Megadimension Neptunia VII
<li>Superdimension Neptune VS Sega Hard Girls
</ul>
<h2>What works - Features</h2>
<ul>
  <li>Character, Map, Accessory, Weapon, Proccessor Unit models should all work.
  <li>Diffuse, Specular, Emission, Normal maps.
    <ul>
      <li>When multiple texture sets are available, they all get imported.
        <br>A random matching set is chosen on import.
        <br>You can select different sets easily with the material drop down in the node editor.
        <br>If you want a matching set, you'll need to change each material slot to match the folder that they came from.
        <br>Each material is named like this -> <code>MaterialName + "_" + FolderName</code>
    </ul>
  <li>Alpha maps are easily enabled in the Node Editor:
    <ol>
      <li>Make a noodle from Node['DiffuseTexture'].Alpha to Node['Principled BSDF'].Alpha.
      <li>Enable Alpha.
      <li>You will often want to disable 'back-face culling'.
    </ol>
  <li>Vertex coloring.
</ul>

<h2>What Doesn't Work - Known Problems</h2>
<h3>Characters with no Face Textures</h3>
The more advanced characteres have a combination of textures to create the face. I did not get around to creating face assembly script yet.
<br>The UV's are there. So; assigning the face texture and transforming the UV's to fit should be easy to do manually.
<h3>Geometry Problems</h3>
So far I've only come across this with maps. I beilieve it happens when a model has double sided geometry. Blender will not allow this.
<br>Instead of cancelling the import of the model, I discard the problem geometry and add the model anyway.
<br>Some geometry may be missing. You may not even notice. All the custom normals will also be discarded.
<br>When this happens you will see a 'Serious Error' popup. This is so you are aware that some of the model data is missing.

<h1>Importing from ISM2</h1>
Blender Menus -> 'File > Import > Neptunia Models (.ism2)'

<h2>Games Files Must Be Extracted Before Using this Blender Add-On</h2>
You must do this yourself:
<ul>
  <li>Extract 'pac' file collections. Specifically the "GAME#####.pac" files.
    <br>Merge all the extracted folders for reliable results. All "GAME#####.pac" should go into a single "GAME" folder.
  <li>Extract 'cl3' file collections.
  <li>Convert 'tid' files to 'png' files
  <li>A trick to extract all the 'cl3' files quickly and then all 'tid' files are as follows:
    <ol>
      <li>Navigate to the 'parent-of-all-cl3-files' directory. (Example: that "GAME" folder you made.)
      <li>Now do a file search for "*.cl3"
      <li>You can only select so many files at a time but select as many as you can before your os throws an error.
        <br>The error will only show when you drag the files over another file.
      <li>Drag these files over the appropriate "extractor.exe". All files will get dumped in their appropriate directories.
      <li>Select the next bunch of files and continue untill you've done all of them.
      <li>Repeat this process for "*.tid" files.
    </ol>
</ul>

<h2>File Extractors</h2>
<ul>
  <li>Hyperdimension Neptunia Re;Birth1
    <br>Hyperdimension Neptunia Re;Birth2
    <br> --> https://steamcommunity.com/sharedfiles/filedetails/?id=453717187
  <li>Hyperdimension Neptunia Re;Birth3
    <br>Megadimension Neptunia Victory II
    <br>Superdimension Neptune VS Sega Hard Girls
    <br> --> https://github.com/MysteryDash/Dash.FileFormats
</ul>

<h2>CREDIT</h2>
<b>Random Talking Brush, howie</b>
<br>This script was written by me (LilacDogoo) based on a 3ds Max script written by Random Talking Bush.
<br>The 3ds Max script written by Random Talking Bush is based on the LightWave importer by howfie.
<br>If you use it, consider giving thanks to Idea Factory, Compile Heart, howfie, Random Talking Bush, and myself.

<h1>Extracting ARC files</h1>
Currently only tested against 'Megadimension Neptunia VII' arc files. May work with other arc files.

<h2>How to More Easily Use VII DLCs</h2>
<ol>
<li>Blender Menus -> 'NepTools > Generate VII DLC Descriptions'.
  <br>This creates a, more easy to scan through, list of you DLCs.
<li>Use the Text Editor within blender to view the 'DLC_descriptions.txt' that was created.
<li>Search for 'swim' to find all the swimsuit models. (Example)
<li>In this case we can see that 'Uzume Swimsuit Set' is listed under 'DLC000000000009500000'
<li>Blender Menus -> 'NepTools > Extract Arc File' (locate 'DLC000000000009500000').
  <br>A folder was created with the same name and location of the arc file.
<li>Blender Menus -> 'NepTools > ISM2 Importer (Neptunia)' (locate the ISM2 file within the extracted files).
</ol>
