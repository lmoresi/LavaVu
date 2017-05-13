/*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
** Copyright (c) 2010, Monash University
** All rights reserved.
** Redistribution and use in source and binary forms, with or without modification,
** are permitted provided that the following conditions are met:
**
**       * Redistributions of source code must retain the above copyright notice,
**          this list of conditions and the following disclaimer.
**       * Redistributions in binary form must reproduce the above copyright
**         notice, this list of conditions and the following disclaimer in the
**         documentation and/or other materials provided with the distribution.
**       * Neither the name of the Monash University nor the names of its contributors
**         may be used to endorse or promote products derived from this software
**         without specific prior written permission.
**
** THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
** "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
** THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
** PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
** BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
** CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
** SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
** HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
** LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
** OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
**
**
** Contact:
*%  Owen Kaluza - Owen.Kaluza(at)monash.edu
*%
*% Development Team :
*%  http://www.underworldproject.org/aboutus.html
**
**~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*/

#ifndef LavaVu__
#define LavaVu__

#include "DrawState.h"
#include "Util.h"
#include "GraphicsUtil.h"
#include "ColourMap.h"
#include "Geometry.h"
#include "View.h"
#include "ViewerApp.h"
#include "Model.h"
#include "VideoEncoder.h"

#define MAX_MSG 256

#define RESET_NO   0
#define RESET_YES  1
#define RESET_ZOOM 2

typedef enum
{
  lucExportNone,
  lucExportCSV,
  lucExportJSON,
  lucExportJSONP,
  lucExportGLDB,
  lucExportGLDBZ,
  lucExportIMAGE
} lucExportType;

class LavaVu : public ViewerApp
{
protected:
  bool verbose, hideall, dbpath;
  std::string defaultScript;

  int viewset;
  int initfigure;
  bool writeimage;
  int writemovie;
  DrawingObject *volume;
  int repeat;
#ifdef HAVE_LIBAVCODEC
  VideoEncoder* encoder;
#else
  //Ensure LavaVu class is same size in case linked from executable compiled
  //with different definitions (this was the cause of a hard to find bug)
  void* encoder;
#endif

  std::vector<Model*> models;

  // Loaded model parameters
  int startstep, endstep;
  lucExportType dump;
  int dumpid;
  int model;
  int tracersteps;

  //Interaction: Key command entry
  std::string entry;
  std::vector<std::string> history;
  std::vector<std::string> linehistory;
  std::vector<std::string> replay;

  TriSurfaces* axis;
  Lines* rulers;
  QuadSurfaces* border;

  unsigned int idle;
  std::chrono::time_point<std::chrono::system_clock> frametime;
  int fps, framecount;

public:
  bool loop;
  int animate;
  bool status;
  bool objectlist;
  char message[MAX_MSG];
  std::string help;
  std::string binpath;

  int view;

  Model* amodel; //Active model
  View* aview;   //Active viewport
  DrawingObject* aobject; //Selected object

  LavaVu(std::string binpath, bool omegalib=false);
  void defaults();
  virtual ~LavaVu();

  //Argument parser
  virtual void arguments(std::vector<std::string> args);
  //Execute function
  void run(std::vector<std::string> args={});
  void clearAll(bool objects=false);

  std::string exportData(lucExportType type, DrawingObject* obj=NULL);

  void parseProperties(std::string& properties);
  void parseProperty(std::string& data);
  void printProperties();
  void printDefaultProperties();

  void reloadShaders();

  void addTriangles(DrawingObject* obj, float* a, float* b, float* c, int level);
  void readHeightMap(const FilePath& fn);
  void readHeightMapImage(const FilePath& fn);
  void readOBJ(const FilePath& fn);
  void readRawVolume(const FilePath& fn);
  void readXrwVolume(const FilePath& fn);
  void readVolumeCube(const FilePath& fn, GLubyte* data, int width, int height, int depth, float min[2], float max[3], int channels=1);
  void readVolumeSlice(const FilePath& fn);
  void readVolumeSlice(const std::string& name, GLubyte* imageData, int width, int height, int channels, bool flip=false);
  void readVolumeTIFF(const FilePath& fn);
  void createDemoModel(unsigned int numpoints);
  void createDemoVolume();
  void newModel(std::string name, int bg=0, float mmin[3]=NULL, float mmax[3]=NULL);
  DrawingObject* addObject(DrawingObject* obj);
  void setOpacity(unsigned int id, float opacity);

  //*** Our application interface:

  // Virtual functions for window management
  virtual void open(int width, int height);
  virtual void resize(int new_width, int new_height);
  virtual void display(bool redraw=true);
  virtual void close();

  // Virtual functions for interactivity
  virtual bool mouseMove(int x, int y);
  virtual bool mousePress(MouseButton btn, bool down, int x, int y);
  virtual bool mouseScroll(float scroll);
  virtual bool keyPress(unsigned char key, int x, int y);

  float parseCoord(const json& val);
  float parseCoord(const std::string& str);
  virtual bool parseCommands(std::string cmd);
  bool parseCommand(std::string cmd, bool gethelp=false);
  bool parsePropertySet(std::string cmd);
  virtual std::string requestData(std::string key);
  //***

  void resetViews(bool autozoom=false);
  void viewSelect(int idx, bool setBounds=false, bool autozoom=false);
  void viewApply(int idx);

  GeomData* getFilledGeometry(DrawingObject* obj);
  void displayObjectList(bool console=true);
  void printMessage(const char *fmt, ...);
  void text(const std::string& str, int xpos=10, int ypos=0, float scale=1.0, Colour* colour=NULL);
  void displayText(const std::string& str, int lineno=1, Colour* colour=NULL);
  void displayMessage();
  void drawColourBar(DrawingObject* draw, int startx, int starty, int length, int height);
  void drawScene(void);
  void drawSceneBlended();

  void drawRulers();
  void drawRuler(DrawingObject* obj, float start[3], float end[3], float labelmin, float labelmax, int ticks, int axis, int tickdir=1);
  void drawBorder();
  void drawAxis();

  std::string video(std::string filename, int fps=30, int width=0, int height=0, int start=0, int end=0);
  std::string encodeVideo(std::string filename="", int fps=30);
  void writeSteps(bool images, int start, int end);

  //data loading
  virtual bool loadFile(const std::string& file);
  void defaultModel();
  void loadModel(FilePath& fn);
  bool loadModelStep(int model_idx, int at_timestep=-1, bool autozoom=false);
  bool tryTimeStep(int ts);

  //Interactive command & script processing
  bool parseChar(unsigned char key);
  Geometry* getGeometryType(std::string what);
  DrawingObject* lookupObject(PropertyParser& parsed, const std::string& key, int idx=0);
  DrawingObject* lookupObject(const std::string& name, DrawingObject* def=NULL);
  std::vector<DrawingObject*> lookupObjects(PropertyParser& parsed, const std::string& key, int start=0);
  Geometry* lookupObjectContainer(DrawingObject* obj, std::string gtype="");
  int lookupColourMap(PropertyParser& parsed, const std::string& key, int idx=0);
  std::vector<std::string> commandList(std::string category="");
  void helpCommand(std::string cmd);
  void dumpCSV(DrawingObject* obj=NULL);
  std::string jsonWriteFile(DrawingObject* obj=NULL, bool jsonp=false, bool objdata=true);
  void jsonWriteFile(std::string fn, DrawingObject* obj=NULL, bool jsonp=false, bool objdata=true);
  void jsonReadFile(std::string fn);

  std::vector<GeomData*> getAllGeometry(DrawingObject* target);

  //Python interface functions
  void render();
  void init();
  std::string image(std::string filename="", int width=0, int height=0, int jpegquality=0);
  std::string web(bool tofile=false);
  int colourMap(std::string name, std::string colours="", std::string properties="");
  DrawingObject* colourBar(DrawingObject* obj);
  void setState(std::string state);
  std::string getState();
  std::string getFigures();
  std::string getTimeSteps();

  void setObject(DrawingObject* target, std::string properties);
  DrawingObject* createObject(std::string properties);
  DrawingObject* getObject(const std::string& name);
  DrawingObject* getObject(int id=-1);
  void reloadObject(DrawingObject* target);

  void loadTriangles(DrawingObject* target, std::vector< std::vector <float> > array, int split=0);
  void loadColours(DrawingObject* target, std::vector <std::string> list);
  void label(DrawingObject* target, std::vector <std::string> labels);

  void clearObject(DrawingObject* target);
  void clearValues(DrawingObject* target, std::string label="");
  void clearData(DrawingObject* target, lucGeometryDataType type);

  //Numpy interface
  void arrayUChar(DrawingObject* target, unsigned char* array, int len, lucGeometryDataType type=lucRGBData);
  void arrayUInt(DrawingObject* target, unsigned int* array, int len, lucGeometryDataType type=lucRGBAData);
  void arrayFloat(DrawingObject* target, float* array, int len, lucGeometryDataType type=lucVertexData);
  void arrayFloat(DrawingObject* target, float* array, int len, std::string label);
  void textureUChar(DrawingObject* target, unsigned char* array, int len, unsigned int width, unsigned int height, unsigned int channels, bool flip=true);
  void textureUInt(DrawingObject* target, unsigned int* array, int len, unsigned int width, unsigned int height, unsigned int channels, bool flip=true);

  int getGeometryCount(DrawingObject* target);
  GeomData* getGeometry(DrawingObject* target, int index);
  void geometryArrayUChar(GeomData* geom, unsigned char* array, int len, lucGeometryDataType type);
  void geometryArrayUInt(GeomData* geom, unsigned int* array, int len, lucGeometryDataType type);
  void geometryArrayFloat(GeomData* geom, float* array, int len, lucGeometryDataType type);
  void geometryArrayFloat(GeomData* geom, float* array, int len, std::string label);

  void geometryArrayViewFloat(GeomData* geom, lucGeometryDataType dtype, float** array, int* len);
  void geometryArrayViewUInt(GeomData* geom, lucGeometryDataType dtype, unsigned int** array, int* len);
  void geometryArrayViewUChar(GeomData* geom, lucGeometryDataType dtype, unsigned char** array, int* len);

  void imageBuffer(unsigned char* array, int width, int height, int depth);
  std::string imageJPEG(int width, int height, int quality=95);
  std::string imagePNG(int width, int height, int depth);

  void isosurface(DrawingObject* target, DrawingObject* source, bool clearvol=false);
  void update(DrawingObject* target, bool compress=true);
  void update(DrawingObject* target, lucGeometryType type, bool compress=true);

  //For testing via python
  std::vector<float> imageArray(std::string path="", int width=0, int height=0, int channels=4);
  float imageDiff(std::string path1, std::string path2="", int downsample=4);
  void queueCommands(std::string cmds);

};

#endif //LavaVu__
