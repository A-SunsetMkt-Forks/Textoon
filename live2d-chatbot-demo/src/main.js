import * as PIXI from 'pixi.js';
import $ from "jquery";
import { Live2DModel } from 'pixi-live2d-display/cubism4';
import { MotionPriority } from 'pixi-live2d-display';
import { Ticker } from '@pixi/ticker';
window.PIXI = PIXI;

// const app = new PIXI.Application({
//     view: document.getElementById("canvas2"),
//     autoStart: true,
//     // resizeTo: window,
//     width: 800,
//     height: 2000,
//   });
const app = new PIXI.Application({
    view: document.getElementById("canvas2"),
    autoStart: true,
    resizeTo: window,
    backgroundColor: 0x000000, // set background color
});
 

const cubism4Model_gen ="assets/20250417-200114_model/female_01Arkit_6.model3.json";
const model_gen = await Live2DModel.from(cubism4Model_gen,{ autoUpdate: false, autoInteract: false } );
 
// set model_gen location and scale
model_gen.anchor.set(0.5); // anchor to center
model_gen.x = app.screen.width / 3; // x center
model_gen.y = app.screen.height / 2; // y center

// set model scale
const scale = Math.min(0.6);
model_gen.scale.set(scale);

// Updating manually
const ticker = new Ticker();
let model = null;
model = model_gen;
app.stage.addChild(model_gen);
draggable(model);

// model.internalModel.motionManager.groups.idle = 'main_idle';
app.ticker.add(() => {
  // mimic the interpolation value, 0-1
  model.update(ticker.elapsedMS);
});

let mouthJawOpen =0;
let mouthClose =0;
let mouthFunnel =0;
let mouthPucker =0;
let mouthStretchLeft =0;
let mouthStretchRight =0;
let mouthLeft =0;
let mouthRight =0;
let mouthSmile =0;
let mouthFrownLeft =0;
let mouthFrownRight =0;
let mouthShrugUpper =0;
let mouthShrugLower =0;
let mouthUpperUpLeft =0;
let mouthUpperUpRight =0;
let mouthLowerDownLeft =0;
let mouthLowerDownRight =0;
let mouthRollUpper =0;
let mouthRollLower =0;
let mouthPressLeft =0;
let mouthPressRight =0;
let mouthCheekPuff =0;
let mouthDimpleLeft =0;
let mouthDimpleRight =0;
let headX =0;
let headY =0;
let headZ =0;

const updateFn = model.internalModel.motionManager.update;
model.internalModel.motionManager.update = () => {
    updateFn.call(model.internalModel.motionManager, model.internalModel.coreModel, Date.now()/1000);

    if(mouthJawOpen==null)
        mouthJawOpen = Math.sin(performance.now() / 100) / 2 + 0.5; // mimic the interpolation value, 0-1

    fetch('assets/20250417-200114_model/config.json')
        .then(response => response.json())
        .then(data => {
            // read setparameter
            const parameters = data.setparameter;
            
            for (let param in parameters) {
                model.internalModel.coreModel.setParameterValueById(param, parameters[param]);
            }
        })
        .catch(error => console.error('Error fetching config.json:', error));

    model.internalModel.coreModel.setParameterValueById("ParamJawOpen", mouthJawOpen);
    model.internalModel.coreModel.setParameterValueById("ParamMouthClose", mouthClose);
    model.internalModel.coreModel.setParameterValueById("ParamMouthFunnel", mouthFunnel);
    model.internalModel.coreModel.setParameterValueById("ParamMouthPucker", mouthPucker);
    model.internalModel.coreModel.setParameterValueById("ParamMouthStretchLeft", mouthStretchLeft);
    model.internalModel.coreModel.setParameterValueById("ParamMouthStretchRight", mouthStretchRight);
    model.internalModel.coreModel.setParameterValueById("ParamMouthLeft", mouthLeft);
    model.internalModel.coreModel.setParameterValueById("ParamMouthRight", mouthRight);
    model.internalModel.coreModel.setParameterValueById("MouthSmileLeft", mouthSmile);
    model.internalModel.coreModel.setParameterValueById("MouthFrownLeft", mouthFrownLeft);
    model.internalModel.coreModel.setParameterValueById("MouthFrownRight", mouthFrownRight);
    model.internalModel.coreModel.setParameterValueById("MouthShrugUpper", mouthShrugUpper);
    model.internalModel.coreModel.setParameterValueById("MouthShrugLower", mouthShrugLower);
    model.internalModel.coreModel.setParameterValueById("MouthUpperUpLeft", mouthUpperUpLeft);
    model.internalModel.coreModel.setParameterValueById("MouthUpperUpRight", mouthUpperUpRight);
    model.internalModel.coreModel.setParameterValueById("ParamMouthLowerDownLeft", mouthLowerDownLeft);
    model.internalModel.coreModel.setParameterValueById("ParamMouthLowerDownRight", mouthLowerDownRight);
    model.internalModel.coreModel.setParameterValueById("ParamMouthRollUpper", mouthRollUpper);
    model.internalModel.coreModel.setParameterValueById("ParamMouthRollLower", mouthRollLower);
    model.internalModel.coreModel.setParameterValueById("ParamMouthPressLeft", mouthPressLeft);
    model.internalModel.coreModel.setParameterValueById("ParamMouthPressRight", mouthPressRight);
    model.internalModel.coreModel.setParameterValueById("MouthCheekPuff", mouthCheekPuff);
    model.internalModel.coreModel.setParameterValueById("ParamMouthDimpleLeft", mouthDimpleLeft);
    model.internalModel.coreModel.setParameterValueById("ParamMouthDimpleRight", mouthDimpleRight);
    model.internalModel.coreModel.setParameterValueById("ParamAngleX", headX);
    model.internalModel.coreModel.setParameterValueById("ParamAngleY", headY);
    model.internalModel.coreModel.setParameterValueById("ParamAngleZ", headZ);
}

function setARKitMouth( _data) {
    // console.log(`mouthpucker=${parseFloat(_data.mouthpucker)}`);
    mouthJawOpen = parseFloat(_data.jawopen);
    mouthClose = parseFloat(_data.mouthclose);
    mouthFunnel = parseFloat(_data.mouthfunnel);
    mouthPucker = parseFloat(_data.mouthpucker);
    mouthStretchLeft = parseFloat(_data.mouthstretchleft);
    mouthStretchRight = parseFloat(_data.mouthstretchright);
    mouthLeft = parseFloat(_data.mouthleft);
    mouthRight = parseFloat(_data.mouthright);
    mouthSmile = parseFloat(_data.mouthsmile);
    mouthFrownLeft = parseFloat(_data.mouthfrownleft);
    mouthFrownRight = parseFloat(_data.mouthfrownright);
    mouthShrugUpper = parseFloat(_data.mouthshrugupper);
    mouthShrugLower = parseFloat(_data.mouthshruglower);
    mouthUpperUpLeft = parseFloat(_data.mouthupperupleft);
    mouthUpperUpRight = parseFloat(_data.mouthupperupright);
    mouthLowerDownLeft = parseFloat(_data.mouthlowerdownleft);
    mouthLowerDownRight = parseFloat(_data.mouthlowerdownright);
    mouthRollUpper = parseFloat(_data.mouthrollupper);
    mouthRollLower = parseFloat(_data.mouthrolllower);
    mouthPressLeft = parseFloat(_data.mouthpressleft);
    mouthPressRight = parseFloat(_data.mouthpressright);
    mouthCheekPuff = parseFloat(_data.mouthcheekpuff);
    mouthDimpleLeft = parseFloat(_data.mouthdimpleleft);
    mouthDimpleRight = parseFloat(_data.mouthdimpleright);
    headX = parseFloat(_data.headx);
    headY = parseFloat(_data.heady);
    headZ = parseFloat(_data.headz);
}

function setMouthOpenY( _mouthOpenYValue) {
    
    mouthJawOpen = _mouthOpenYValue;
    mouthClose =0;
    mouthFunnel =0;
    mouthPucker =0;
    mouthStretchLeft =0;
    mouthStretchRight =0;
    mouthLeft =0;
    mouthRight =0;
    mouthSmile =0;
    mouthFrownLeft =0;
    mouthFrownRight =0;
    mouthShrugUpper =0;
    mouthShrugLower =0;
    mouthUpperUpLeft =0;
    mouthUpperUpRight =0;
    mouthLowerDownLeft =0;
    mouthLowerDownRight =0;
    mouthRollUpper =0;
    mouthRollLower =0;
    mouthPressLeft =0;
    mouthPressRight =0;
    mouthCheekPuff =0;
    mouthDimpleLeft =0;
    mouthDimpleRight =0;
    headX =0;
    headY =0;
    headZ =0;
    // if(_mouthValue==100.0)
    //     mouthValue = Math.sin(performance.now() / 100) / 2 + 0.5;
}

function getRandomInt(min, max) {
    min = Math.ceil(min);
    max = Math.floor(max);
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function draggable(model) {
    model.buttonMode = true;
    model.on("pointerdown", (e) => {
      model.dragging = true;
      model._pointerX = e.data.global.x - model.x;
      model._pointerY = e.data.global.y - model.y;
    });
    model.on("pointermove", (e) => {
      if (model.dragging) {
        model.position.x = e.data.global.x - model._pointerX;
        model.position.y = e.data.global.y - model._pointerY;
      }
    });
    model.on("pointerupoutside", () => (model.dragging = false));
    model.on("pointerup", () => (model.dragging = false));
  }


setInterval(()=>{
    $.ajax({
        type : "GET",
        url : "/api/get_mouth_y",
        dataType: 'json',
        async: true,
        success(data) {
            setARKitMouth( data)
        },
    });
}, 1)