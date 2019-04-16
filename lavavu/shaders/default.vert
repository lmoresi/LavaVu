attribute vec4 aVertexPosition;
attribute vec4 aVertexColour;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
varying vec4 vColour;
#ifndef WEBGL
flat varying vec4 vFlatColour;
#endif
void main(void)
{
  gl_Position = uPMatrix * uMVMatrix * aVertexPosition;
  vColour = aVertexColour;
#ifndef WEBGL
  vFlatColour = aVertexColour;
#endif
}

