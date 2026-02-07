let canvas, textbox, gl, shader, batcher, assetManager, skeletonRenderer;
let mvp;
let isRunning = false; // Control flag for engine loop
let DEBUG_HITBOX = false; // Enable hitbox visualization

let lastFrameTime;
let spineDataA, spineDataBG;
let bufferColor = [ 0.3, 0.3, 0.3 ];

const CHARACTER = 'arona_spr';
const BINARY_PATH = '/spine/arona/arona_spr.skel';
const ATLAS_PATH = '/spine/arona/arona_spr.atlas';
const CHARACTER_2 = 'NP0035_spr';
const BINARY_PATH_2 = '/spine/arona/NP0035_spr.skel';
const ATLAS_PATH_2 = '/spine/arona/NP0035_spr.atlas';
const BG_DAY = 'arona_workpage_daytime';
const BINARY_PATH_BG_DAY = '/spine/arona/arona_workpage_daytime.skel';
const ATLAS_PATH_BG_DAY = '/spine/arona/arona_workpage_daytime.atlas';
const BG_NIGHT = 'arona_workpage_nighttime';
const BINARY_PATH_BG_NIGHT = '/spine/arona/arona_workpage_nighttime.skel';
const ATLAS_PATH_BG_NIGHT = '/spine/arona/arona_workpage_nighttime.atlas';

const TEXTBOX_ANCHOR = { x: 1440, y: 1200 };

const LOADOUT = { isday: true, isorganized: true, start: 0, start2: 0, introAudio: null, startAudio: null, interactAudio: null, ux: 50, uy: 50 };

let customScale = 1;
let targetFps = 60;
let bgmfile = '';
let bgmvolume = 0;
let bgm;
let voiceAudio = null;

let alerted = false;
let globalPause = false;

let introAnimation, spoilerChar;
let forcedTime = -1;
let acceptingClick;
let characterOffset = { x: 0, y: 0 };
let introLoop;
let introTrack, sideTrack;
let currentVoiceline = 1;
let mouseSelect = -1;
let trackerID = -1;
let untrackerID = -1;
let unpetID = -1;
let PPointX, PPointY, EPointX, EPointY;
let TPoint, TEye;
let flipped = false;
let displayDialog = true;
let enableIdleLines = false;
let transpose = 1;

// All voicelines are manually timed for duration. This may not be the most optimized solution, but works for all intents and purposes.
const SPOILER_INTRO_AUDIO = [
	{
		text_location: { a: { x: 750, y: 500 }, p: { x: 1100, y: 550 } },
		in: [ 'NP0035/NP0035_Work_AronaSleepSit_In_1_2', 'NP0035/NP0035_Work_AronaSleepSit_In_2_2' ],
		in_dialog: [ "Strawberry milk...?", "Senpai, you should get up soon." ],
		in_speaker: [ "p", "p" ]
	},
	{
		text_location: { a: { x: 750, y: 500 }, p: { x: 1000, y: 300 } },
		in: [ 'NP0035/NP0035_Work_AronaSleepPeek_In_1_2', 'NP0035/NP0035_Work_AronaSleepPeek_In_2_2' ],
		in_dialog: [ "Is she sleeping?", "As I thought, she's sleeping..." ],
		in_speaker: [ "p", "p" ]
	},
	{
		text_location: { a: { x: 750, y: 500 }, p: { x: 1100, y: 550 } },
		in: [ 'NP0035/NP0035_Work_AronaSleepSit_Talk_4_2' ],
		in_dialog: [ "Really?" ],
		in_speaker: [ "p" ]
	}
]

const INTRO_AUDIO_A = [
	{
		text_location: { a: { x: 680, y: 860 }, p: { x: 0, y: 0 } },
		exit: [ 'Arona/Arona_Work_Sleep_Exit_1', 'Arona/Arona_Work_Sleep_Exit_2', 'Arona/Arona_Work_Sleep_Exit_3' ],
		exit_dialog: [ "Wh-wha...huh?", "Ah?!", "...Huh?" ],
		exit_speaker: [ "a", "a", "a" ],
		in: [ 'Arona/Arona_Work_Sleep_In_1', 'Arona/Arona_Work_Sleep_In_2' ],
		in_dialog: [ "Zzz. Strawberry milk... Heeheehee.", "Eat all that? No, I couldn't..." ],
		in_speaker: [ "a", "a" ],
		talk: [ 'Arona/Arona_Work_Sleep_Talk_1', 'Arona/Arona_Work_Sleep_Talk_2', 'Arona/Arona_Work_Sleep_Talk_3', 'Arona/Arona_Work_Sleep_Talk_4', 'Arona/Arona_Work_Sleep_Talk_5', 'Arona/Arona_Work_Sleep_Talk_6' ],
		talk_dialog: [ "Sensei, you're so...", "..Heeheehee.", "Zzz...", "Me? Doze off? Never... Zzz...", "Heehee, yummy...", "No, Sensei... You can't do that..." ],
		talk_speaker: [ "a", "a", "a", "a", "a", "a" ]
	},
	{
		text_location: { a: { x: 1000, y: 350 }, p: { x: 0, y: 0 } },
		exit: [ 'Arona/Arona_Work_Watch_Exit_1', 'Arona/Arona_Work_Watch_Exit_2' ],
		exit_dialog: [ "Ah!", "Huh?" ],
		exit_speaker: [ "a", "a" ],
		in: [ 'Arona/Arona_Work_Watch_In_1', 'Arona/Arona_Work_Watch_In_2' ],
		in_dialog: [ "Another day means another clear sky.", "Hmm... Maybe it'll rain." ],
		in_speaker: [ "a", "a" ],
		talk: [ 'Arona/Arona_Work_Watch_Talk_1', 'Arona/Arona_Work_Watch_Talk_3' ],
		talk_dialog: [ "I wonder what's out there...", "Hmm..." ],
		talk_speaker: [ "a", "a" ]
	},
	{
		text_location: { a: { x: 750, y: 500 }, p: { x: 0, y: 0 } },
		exit: [ 'Arona/Arona_Work_Sit_Exit_1', 'Arona/Arona_Work_Sit_Exit_2', 'Arona/Arona_Work_Sit_Exit_3' ],
		exit_dialog: [ "Eh?", "Huh?", "Ah!" ],
		exit_speaker: [ "a", "a", "a" ],
		in: [ 'Arona/Arona_Work_Sit_In_1' ],
		in_dialog: [ "Mm-hmm...♬" ],
		in_speaker: [ "a" ],
		talk: [ 'Arona/Arona_Work_Sit_Talk_1', 'Arona/Arona_Work_Sit_Talk_2', 'Arona/Arona_Work_Sit_Talk_3' ],
		talk_dialog: [ "La, lala, lala! ♪", "Hmm hmm hmm... ♩", "Oh, I wonder what today will bring! ♬" ],
		talk_speaker: [ "a", "a", "a" ]
	}
];

const INTRO_STARTWORK_A = {
	talk: [ [ 'Arona/Arona_Default_TTS', 'Arona/Arona_Work_In_1'] , 'Arona/Arona_Work_In_2', 'Arona/Arona_Work_In_3', 'Arona/Arona_Work_In_4' ],
	expression: [ [ '12', '12' ], '25', '31', '32' ],
	talk_dialog: [ [ "Sensei! I've been waiting for you!", "Sensei! I've been waiting for you!" ], "Let's get to work!", "Any task you want to do in particular, sensei?", "I can give you a hand with whatever you want!" ],
};

const INTERACT_AUDIO_A = {
	talk: [ 'Arona/Arona_Work_Talk_1', [ 'Arona/Arona_Default_TTS', 'Arona/Arona_Work_Talk_2' ], 'Arona/Arona_Work_Talk_3', 'Arona/Arona_Work_Talk_4', 'Arona/Arona_Work_Talk_5', 'Arona/Arona_Work_Talk_6', 'Arona/Arona_Work_Talk_7_1' ],
	talk_dialog: [ "Manage tasks you need to complete from here!", [ "Sensei! Pick a task. I'll back you up!", "Sensei! Pick a task. I'll back you up!" ], "Here's everything on your docket. Adults have it rough, huh?", "There's lots of work to do, but I know you can do it!", "Take care of your health too. It's gotta take priority!", "Oh...that's a lot of work.", "You got this, Sensei!" ],
	expression: [ '00', [ '25', '25' ], '13', '12', '18', '29', '25' ]
};

const SPECIAL_AUDIO_A = {
	talk: [ [ "Arona/Arona_Surprise" ], ['Arona/Arona_Frustration'] ],
	talk_dialog: [["Y-You shouldn't touch Arona there, Sensei!" ], [ "W-What are you doing with my skirt!?" ] ],
    expression: [ [ "18", "18" ] , [ "18", "18" ] ],
};

const INTRO_AUDIO_P = [
	{
		text_location: { a: { x: 0, y: 0 }, p: { x: 450, y: 300 } },
		exit: [ 'NP0035/NP0035_Work_Cabinet_Exit_1' ],
		exit_dialog: [ "...Ah." ],
		exit_speaker: [ "p" ],
		in: [ 'NP0035/NP0035_Work_Cabinet_In_1', 'NP0035/NP0035_Work_Cabinet_In_2' ],
		in_dialog: [ "So, that's what this is...", "...So that's how it is." ],
		in_speaker: [ "p", "p" ],
		talk: [ 'NP0035/NP0035_Work_Cabinet_Talk_1', 'NP0035/NP0035_Work_Cabinet_Talk_1' ],
		talk_dialog: [ "Hmm... I see.", "Hmm... So that's how it's structured." ],
		talk_speaker: [ "p", "p" ]
	},
	{
		text_location: { a: { x: 750, y: 500 }, p: { x: 1100, y: 550 } },
		exit: [ 'NP0035/NP0035_Work_Sit_Exit_1' ],
		exit_dialog: [ "Ah." ],
		exit_speaker: [ "p" ],
		in: [ 'NP0035/NP0035_Work_Sit_In_1' , 'NP0035/NP0035_Work_Sit_In_2' ],
		in_dialog: [ "Mmm...", "Hmm..." ],
		in_speaker: [ "p", "p" ],
		talk: [ 'NP0035/NP0035_Work_Sit_Talk_1' ],
		talk_dialog: [ "..." ],
		talk_speaker: [ "p" ]
	},
	{
		text_location: { a: { x: 575, y: 125 }, p: { x: 1300, y: 350 } },
		exit: [ 'NP0035/NP0035_Work_Umbrella_Exit_1' ],
		exit_dialog: [ "Ah." ],
		exit_speaker: [ "p" ],
		in: [ 'NP0035/NP0035_Work_Umbrella_In_1' ],
		in_dialog: [ "If it rains..." ],
		in_speaker: [ "p" ],
		talk: [ 'NP0035/NP0035_Work_Umbrella_Talk_1', 'NP0035/NP0035_Work_Umbrella_Talk_2' ],
		talk_dialog: [ "Would this be useful?", "Me too. Together." ],
		talk_speaker: [ "p", "p" ]
	},
	{
		text_location: { a: { x: 1600, y: 400 }, p: { x: 1250, y: 180 } },
		exit: [ 'NP0035/NP0035_Work_PlanaWatchSky_Exit_1' ],
		exit_dialog: [ "...Ah." ],
		exit_speaker: [ "p" ],
		in: [ [ 'Arona/Arona_Work_PlanaWatchSky_In_1_1', 'NP0035/NP0035_Work_PlanaWatchSky_In_1_2', 'Arona/Arona_Work_PlanaWatchSky_In_1_3' ] ],
		in_dialog: [ [ "Can you see that, Plana-chan?", "Do you mean that, senpai?", "Yes, that!" ] ],
		in_speaker: [ [ "a", "p", "a" ] ],
		talk: [ [ 'Arona/Arona_Work_PlanaWatchSky_Talk_1_1', 'NP0035/NP0035_Work_PlanaWatchSky_Talk_1_2' ] ],
		talk_dialog: [ [ "What about over there?", "Mmm..." ] ],
		talk_speaker: [ [ "a", "p" ] ]
	},
	{
		text_location: { a: { x: 1500, y: 350 }, p: { x: 1100, y: 550 } },
		exit: [ 'NP0035/NP0035_PlanaSitPeek_Exit_1' ],
		exit_dialog: [ "Ah." ],
		exit_speaker: [ "p" ],
		in: [ [ 'Arona/Arona_Work_PlanaSitPeek_In_1_1' , 'NP0035/NP0035_Work_PlanaSitPeek_In_1_2' ] ],
		in_dialog: [ [ "Stare~", "Hmm..." ] ],
		in_speaker: [ [ "a", "p" ] ],
		talk: [ 'NP0035/NP0035_Work_PlanaSitPeek_Talk_1', 'NP0035/NP0035_Work_PlanaSitPeek_Talk_2' ],
		talk_dialog: [ "I can feel your eyes on me.", "I'm in trouble." ],
		talk_speaker: [ "p", "p" ]
	}
];

const INTRO_STARTWORK_P = {
	talk: [ [ 'NP0035/NP0035_Work_In_1_1', 'NP0035/NP0035_Default_TTS', 'NP0035/NP0035_Work_In_1_2' ], 'NP0035/NP0035_Work_In_2', 'NP0035/NP0035_Work_In_3', 'NP0035/NP0035_Work_In_4' ],
	expression: [ [ '02', '03', '03' ], '03', '00', '02' ],
	talk_dialog: [ [ "Connecting.", "Sensei, I've been waiting for you.", "Sensei, I've been waiting for you." ], "It's time to get to work.", "Which task would you like to start with, Sensei?", "On standby. There are numerous tasks that need to be resolved." ],
};

const INTERACT_AUDIO_P = {
	talk: [ 'NP0035/NP0035_Work_Talk_1', [ 'NP0035/NP0035_Default_TTS', 'NP0035/NP0035_Work_Talk_2' ], 'NP0035/NP0035_Work_Talk_3', 'NP0035/NP0035_Work_Talk_4', 'NP0035/NP0035_Work_Talk_5' ],
	talk_dialog: [ "You can carry out your various tasks here, Sensei.", [ "Sensei. Please select whatever task you wish to do.", "Sensei. Please select whatever task you wish to do." ] , "There are many tasks that need to be resolved. Now then, if you please.", "Perplexing. This is a meaningless action. Please do not poke me. Doing so will result in damage.", "Understood. Sensei doesn't have anything in particular to do at the moment, so you're free." ],
	expression: [ '03', [ '03', '03' ], '03', '13', '12' ]
};

const HITBOX = {
	headpat: { xMin: 1330, xMax: 1620, yMin: 615, yMax: 755 },
	face: { xMin: 1360, xMax: 1580, yMin: 770, yMax: 930 },
	chest: { xMin: 1375, xMax: 1565, yMin: 1020, yMax: 1200 },
	skirt: { xMin: 1250, xMax: 1700, yMin: 1250, yMax: 1650 }
};

const HEADPAT_CLAMP = 30;
const EYE_CLAMP_X = 200;
const EYE_CLAMP_Y = EYE_CLAMP_X * (9 / 16)
const HEADPAT_STEP = 5;
const EYE_STEP = 10;
let mousePos = { x: 0, y: 0 };
let volume = 0.5;
let volumeMem = 0.5;
let mouseOptions = { voicelines: true, headpatting: true, mousetracking: true, autotrack: false };

function clamp(num, min, max) {
	return Math.min(Math.max(num, min), max);
}

function idleLines() {
	if (globalPause) return;

	if (!LOADOUT.isday && LOADOUT.start == 1 && LOADOUT.start2 == 1) LOADOUT.start = 4;
	let array = LOADOUT.introAudio[LOADOUT.start];
	let selection = Math.floor(Math.random() * array.talk.length);
	introTrack = playLine(
		{ filepath: array.talk[selection], dialog: array.talk_dialog[selection], dPositions: array.text_location, dSequence: array.talk_speaker[selection] }
	);
	if (spoilerChar && LOADOUT.isday && LOADOUT.start == 0 && LOADOUT.start2 == 0 && selection == 3) {
		introTrack.addEventListener('ended', function() {
			setTimeout(function() {
				sideTrack = playLine(
					{ filepath: SPOILER_INTRO_AUDIO[2].in[0], dialog: SPOILER_INTRO_AUDIO[2].in_dialog[0], dPositions: SPOILER_INTRO_AUDIO[2].text_location, dSequence: SPOILER_INTRO_AUDIO[2].talk_speaker[0] }
				)
			}, 500);
		});
	}
	if (spoilerChar && LOADOUT.isday && LOADOUT.start == 0 && LOADOUT.start2 == 0 && selection == 3) {
		introTrack.addEventListener('ended', function() {
			setTimeout(function() {
				sideTrack = playLine(
					{ filepath: SPOILER_INTRO_AUDIO[2].in[0], dialog: SPOILER_INTRO_AUDIO[2].in_dialog[0], dPositions: SPOILER_INTRO_AUDIO[2].text_location, dSequence: SPOILER_INTRO_AUDIO[2].talk_speaker[0] }
				)
			}, 500);
		});
	}
}

// NOTE: X and Y appears to be inversely related from cursor position to bone adjustment.
//       This behavior's reason is unknown, but it LOOKS right so leave it alone!
function trackMouse() {
	let adjX = (mousePos.x / canvas.width) - 0.5 - (characterOffset.x / (2880 * 2));
	let adjY = (mousePos.y / canvas.height) - 0.5 - (characterOffset.y / (1620 * 2));
	TEye.y = TEye.y - (Math.sign(adjX) * EYE_STEP);
	TEye.x = TEye.x - (Math.sign(adjY) * EYE_STEP);
	TEye.y = clamp(TEye.y, EPointY - (Math.abs(adjX) * EYE_CLAMP_X), EPointY + (Math.abs(adjX) * EYE_CLAMP_X));
	TEye.x = clamp(TEye.x, EPointX - (Math.abs(adjY) * EYE_CLAMP_Y), EPointX + (Math.abs(adjY) * EYE_CLAMP_Y));
}

function untrackMouse() {
	if (Math.abs(TEye.y - EPointY) <= EYE_STEP && Math.abs(TEye.x - EPointX) <= EYE_STEP) {
		if (untrackerID != -1) {
			TEye.y = EPointY;
			TEye.x = EPointX;
			clearInterval(untrackerID);
			untrackerID = -1;
			setTimeout(function (){
				acceptingClick = true;
			}, 500);
		}
	}
	if (TEye.y > EPointY) TEye.y -= EYE_STEP;
	if (TEye.y < EPointY) TEye.y += EYE_STEP;
	if (TEye.x > EPointX) TEye.x -= EYE_STEP;
	if (TEye.x < EPointX) TEye.x += EYE_STEP;
}

function unpet() {
	if (Math.abs(TPoint.x - PPointX) <= HEADPAT_STEP && Math.abs(TPoint.y - PPointY) <= HEADPAT_STEP) {
		if (unpetID != -1) {
			TPoint.x = PPointX;
			TPoint.y = PPointY;
			clearInterval(unpetID);
			unpetID = -1;
			setTimeout(function() {
				acceptingClick = true;
			}, 500);
		}
	}
	if (TPoint.y > PPointY) TPoint.y -= HEADPAT_STEP;
	if (TPoint.y < PPointY) TPoint.y += HEADPAT_STEP;
	if (TPoint.x > PPointX) TPoint.x -= HEADPAT_STEP;
	if (TPoint.x < PPointX) TPoint.x += HEADPAT_STEP;
}

function updateTextboxPosition() {
    if (!textbox) return;
    // Always force anchor position regardless of voice data to keep "centered around model"
    textbox.style.left = tInvert(TEXTBOX_ANCHOR.x, 'x') + 'px';
    textbox.style.top = tInvert(TEXTBOX_ANCHOR.y, 'y') + 'px';
}

function playLine(voiceData, endFunc, spine) {
	let audioDir = 'audio';
	// FIX: Update base path for Next.js public folder structure
	const basePath = '/spine/arona';
	let parentTrack;
	if (typeof(voiceData.filepath) == 'string') {
		// FIX: Check if path already contains lowercase or complex struct
        // Force lowercase logic to catch linux sensitivity
        let normalizedDir = audioDir;
        let pathParts = voiceData.filepath.split('/');
        let finalPathStr = '';
        if (pathParts.length > 1) {
             // Folder part (keep case) + Filename part (lowercase)
             finalPathStr = `${pathParts[0]}/${pathParts[1].toLowerCase()}`;
        } else {
             finalPathStr = voiceData.filepath.toLowerCase();
        }
        
		let track = new Audio(`${basePath}/${normalizedDir}/${finalPathStr}.ogg`);
		if (voiceData.expression && spine) spine.state.setAnimation(1, voiceData.expression, true);
		track.volume = volume;
		
        const cleanup = () => {
			textbox.style.opacity = 0;
			voiceAudio = null;
			if (endFunc) endFunc();
        };

		// FIX: Catch play errors and ensure cleanup
		track.play().catch(e => {
            console.warn("[ARONA] Audio play failed (user interaction needed):", e);
            // If failed, cleanup immediately or after a short delay
            setTimeout(cleanup, 1000); 
        });

        // FORCE ANCHOR POSITION
        updateTextboxPosition();

		textbox.innerHTML = voiceData.dialog;
		if (displayDialog) textbox.style.opacity = 1;

		track.addEventListener('ended', cleanup);

		parentTrack = track;
	}
	else {
		let prevtrack;
        let normalizedDir = audioDir;
		for (let i = 1; i <= voiceData.filepath.length; i++) {
			// FIX: Use absolute path and correct audio dir and lowercase
            let rawPath = voiceData.filepath[i - 1];
            let pathParts = rawPath.split('/');
            let finalPathStr = '';
            if (pathParts.length > 1) {
                finalPathStr = `${pathParts[0]}/${pathParts[1].toLowerCase()}`;
            } else {
                finalPathStr = rawPath.toLowerCase();
            }
			let track = new Audio(`${basePath}/${normalizedDir}/${finalPathStr}.ogg`);
			if (i == 1) {
				parentTrack = track;
			}
			track.volume = volume;
			if (!prevtrack) {
                // FORCE ANCHOR POSITION
                updateTextboxPosition();

				if (voiceData.expression && voiceData.expression[i - 1] && spine) spine.state.setAnimation(1, voiceData.expression[i - 1], true);
				track.play();
				textbox.innerHTML = voiceData.dialog[i - 1];
				if (displayDialog) textbox.style.opacity = 1;
				prevtrack = track;
			}
			else {
				prevtrack.addEventListener('ended', function() {
					if (voiceData.expression && voiceData.expression[i - 1] && spine) spine.state.setAnimation(1, voiceData.expression[i - 1], true);
					
                    // FORCE ANCHOR POSITION
                    updateTextboxPosition();

					track.play();
					textbox.innerHTML = voiceData.dialog[i - 1];

					introTrack = track;
				});

				prevtrack = track;
			}
			if (i == voiceData.filepath.length) {
				track.addEventListener('ended', function() {
					textbox.style.opacity = 0;
					voiceAudio = null;
					endFunc();
				});
			}
		}
	}

	return parentTrack;
}

// Textbox Position Scaling (inverse of Hitbox Scaling)
function tInvert(n, side) {
	let d = { x: { length: 2880, mid: (canvas.width / 2) }, y: { length: 1620, mid: (canvas.height / 2) } }
	n = n - (d[side].length * 0.5);
	n = (n / transpose) * customScale;
	return (n + d[side].mid);
}

// Hitbox Scaling
function t(n, side) {
	let d = { x: { length: 2880, mid: (canvas.width / 2) }, y: { length: 1620, mid: (canvas.height / 2) } }
	n = n - d[side].mid;
	n = (n * transpose) / customScale;
	return ((d[side].length * 0.5) + n);
}

// -1 = [No Entry], 1 = Headpat, 2 = Voiceline, 3 = Eye Track
function pressedMouse(x, y, overrideTrack = false) {
	tx = t(x, 'x');
	ty = t(y, 'y');
	if (!alerted && tx < 1440) {
		if (introLoop) {
			clearInterval(introLoop);
			introLoop = null;
		}
		if (introTrack) {
			introTrack.pause();
			introTrack = null;
		}
		if (sideTrack) {
			sideTrack.pause();
			sideTrack = null;
		}

		spineDataBG.state.addAnimation(2, `Idle_0${LOADOUT.start}_Touch_M`, false, 0);
		spineDataBG.state.addAnimation(3, `Idle_0${LOADOUT.start}_Touch_A`, false, 0);

		if (LOADOUT.isday && LOADOUT.start == 0 && spoilerChar) {
			spineDataBG.state.addAnimation(5, `Idle_1${(LOADOUT.start2 + 1)}_Touch_M`, false, 0);
			spineDataBG.state.addAnimation(6, `Idle_1${(LOADOUT.start2 + 1)}_Touch_A`, false, 0);
		}

		if (!LOADOUT.isday && LOADOUT.start == 1 && LOADOUT.start2 == 1) {
			spineDataBG.state.addAnimation(5, 'Idle_11_Touch_M', false, 0);
			spineDataBG.state.addAnimation(6, 'Idle_11_Touch_A', false, 0);
		}

		let array = LOADOUT.introAudio[LOADOUT.start];
		let selection = Math.floor(Math.random() * array.exit.length);

        // FIX: Use playLine logic to handle paths and errors consistently
        voiceAudio = playLine(
            { 
                filepath: array.exit[selection], 
                dialog: array.exit_dialog[selection], 
                dPositions: array.text_location, 
                dSequence: array.exit_speaker[selection] 
            },
            function() {
                spineDataBG.state.setAnimation(0, 'Idle_background_00', true);
                spineDataBG.state.setEmptyAnimation(1, 0);
                spineDataBG.state.setEmptyAnimation(2, 0);
                spineDataBG.state.setEmptyAnimation(3, 0);
                spineDataBG.state.setEmptyAnimation(4, 0);
                spineDataBG.state.setEmptyAnimation(5, 0);
                spineDataBG.state.setEmptyAnimation(6, 0);
            
                setTimeout(function() {
                    alerted = true;
                    spineDataA.state.setAnimation(0, 'Idle_01', true);
                    let selection = Math.floor(Math.random() * 4);
                    voiceAudio = playLine(
                        { filepath: LOADOUT.startAudio.talk[selection], dialog: LOADOUT.startAudio.talk_dialog[selection], expression: LOADOUT.startAudio.expression[selection] },
                        function() {
                            spineDataA.state.setAnimation(1, '00', true);
                            acceptingClick = true;
                        },
                        spineDataA
                    )
                }, 500);
            },
            null
        );
	}
	else if (!overrideTrack && mouseSelect <= 0 && tx > (HITBOX.headpat.xMin + characterOffset.x) && tx < (HITBOX.headpat.xMax + characterOffset.x) && ty > (HITBOX.headpat.yMin - characterOffset.y) && ty < (HITBOX.headpat.yMax - characterOffset.y) && mouseOptions.headpatting) {
		spineDataA.state.setAnimation(1, 'Pat_01_M', false);
		spineDataA.state.setAnimation(2, 'Pat_01_A', false);
		mouseSelect = 1;
	}
	else if (!overrideTrack && mouseSelect <= 0 && tx > (HITBOX.face.xMin + characterOffset.x) && tx < (HITBOX.face.xMax + characterOffset.x) && ty > (HITBOX.face.yMin - characterOffset.y) && ty < (HITBOX.face.yMax - characterOffset.y) && mouseOptions.voicelines) {
		mouseSelect = 2;
	}
    else if (!overrideTrack && mouseSelect <= 0 && tx > (HITBOX.chest.xMin + characterOffset.x) && tx < (HITBOX.chest.xMax + characterOffset.x) && ty > (HITBOX.chest.yMin - characterOffset.y) && ty < (HITBOX.chest.yMax - characterOffset.y) && mouseOptions.voicelines) {
        mouseSelect = 4;
    }
    else if (!overrideTrack && mouseSelect <= 0 && tx > (HITBOX.skirt.xMin + characterOffset.x) && tx < (HITBOX.skirt.xMax + characterOffset.x) && ty > (HITBOX.skirt.yMin - characterOffset.y) && ty < (HITBOX.skirt.yMax - characterOffset.y) && mouseOptions.voicelines) {
        mouseSelect = 5;
    }
	else if (mouseOptions.mousetracking) {
		if (trackerID == -1) {
			trackerID = setInterval(trackMouse, 20);
		}
		spineDataA.state.setEmptyAnimation(1, 0);
		spineDataA.state.setEmptyAnimation(2, 0);
		let eyetracking = spineDataA.state.addAnimation(1, 'Look_01_M', false, 0);
		eyetracking.mixDuration = 0.2;
		if (LOADOUT.isday) {
			let eyetracking2 = spineDataA.state.addAnimation(2, 'Look_01_A', false, 0);
			eyetracking2.mixDuration = 0.2;
		}
		mousePos.x = x;
		mousePos.y = y;
		mouseSelect = 3;
	}
	else if (mouseSelect == -1) {
		acceptingClick = true;
	}
}

let idleMovement = 0;
let idleTimeout = -1;
let idleMax = 10; //expressed in 100ms/unit
let minMovement = 50;

function autoTimeout() {
	idleMovement = idleMovement + 1;
	if (idleMovement >= idleMax && idleTimeout != -1) {
		clearInterval(idleTimeout);
		idleTimeout = -1;
		releasedMouse(0, 0);

		// Will not auto-track again until 3 seconds have passed since last tracking
		setTimeout(function() {
			idleMovement = 0;
		}, 3000);
	}
}

function movedMouse(x, y, deltaX, deltaY) {
	let v = Math.sqrt((deltaX * deltaX) + (deltaY * deltaY)) > minMovement;
	if (mouseOptions.autotrack && mouseSelect <= 0 && v && acceptingClick && alerted && idleMovement <= 0) {
		mouseSelect = 3;
		pressedMouse(x, y, true);
		acceptingClick = false;
		idleTimeout = setInterval(autoTimeout, 100);
	}
	switch (mouseSelect) {
		case 1:
			if ((y < 810 && deltaY < 0) || (x >= 1440 && deltaX > 0)) {
				TPoint.y = clamp(TPoint.y - HEADPAT_STEP, PPointY - HEADPAT_CLAMP, PPointY + HEADPAT_CLAMP);
			}
			else if ((y >= 810 && deltaY > 0) || (x < 1440 && deltaX < 0)) {
				TPoint.y = clamp(TPoint.y + HEADPAT_STEP, PPointY - HEADPAT_CLAMP, PPointY + HEADPAT_CLAMP);
			}
			break;
		case 2:
			mouseSelect = -1;
			acceptingClick = true;
			break;
        case 4: 
        case 5:
            mouseSelect = -1;
            acceptingClick = true;
            break;
		case 3:
			mousePos.x = x;
			mousePos.y = y;
			if (v) idleMovement = 0;
			break;
		default:
	}
}

function releasedMouse(x, y) {
	switch (mouseSelect) {
		case 1:
			if (unpetID == -1) {
				unpetID = setInterval(unpet, 20);
			}
			spineDataA.state.setAnimation(1, 'PatEnd_01_M', false);
			spineDataA.state.setAnimation(2, 'PatEnd_01_A', false);
			spineDataA.state.addEmptyAnimation(1, 0.5, 0);
			spineDataA.state.addEmptyAnimation(2, 0.5, 0);
			break;
		case 2:
			let selection = Math.floor(Math.random() * LOADOUT.interactAudio.talk.length);
			voiceAudio = playLine(
				{ filepath: LOADOUT.interactAudio.talk[selection], dialog: LOADOUT.interactAudio.talk_dialog[selection], expression: LOADOUT.interactAudio.expression[selection] },
				function() {
					spineDataA.state.setAnimation(1, '00', true);
					acceptingClick = true;
				},
				spineDataA
			);
			break;
        case 4: // Chest
            voiceAudio = playLine(
                { filepath: SPECIAL_AUDIO_A.talk[0], dialog: SPECIAL_AUDIO_A.talk_dialog[0], expression: SPECIAL_AUDIO_A.expression[0] },
                function() {
                    spineDataA.state.setAnimation(1, '00', true);
                    acceptingClick = true;
                },
                spineDataA
            );
            break;
        case 5: // Skirt
            voiceAudio = playLine(
                { filepath: SPECIAL_AUDIO_A.talk[1], dialog: SPECIAL_AUDIO_A.talk_dialog[1], expression: SPECIAL_AUDIO_A.expression[1] },
                function() {
                    spineDataA.state.setAnimation(1, '00', true);
                    acceptingClick = true;
                },
                spineDataA
            );
            break;
		case 3:
			if (trackerID != -1) {
				clearInterval(trackerID);
				trackerID = -1;
			}
			if (untrackerID == -1) {
				untrackerID = setInterval(untrackMouse, 20);
			}
			let eyetracking = spineDataA.state.setAnimation(1, 'LookEnd_01_M', false);
			let eyetracking2 = spineDataA.state.setAnimation(2, 'LookEnd_01_A', false);
			eyetracking.mixDuration = 0;
			eyetracking2.mixDuration = 0;
			spineDataA.state.addEmptyAnimation(1, 0.5, 0);
			spineDataA.state.addEmptyAnimation(2, 0.5, 0);
			break;
		default:
	}
	mouseSelect = -1;
}

function setMouse(event) {
    let rect = canvas.getBoundingClientRect();
	let ax = event.clientX - rect.left;
	let ay = event.clientY - rect.top;
    
    // Scale coordinates if canvas display size differs from internal resolution
    // Internal resolution logic in t() assumes 2880x1620 conceptual space scaled to canvas
    // But t() takes 'n' which is raw pixel coord on canvas.
    
	let mx = 1;
	if (flipped) {
		mx = -1;
		ax = canvas.width - ax;
	}

	return { x: ax, y: ay, m: mx }
}

function init() {
    isRunning = true;
    console.log("[ARONA] Engine Init started...");
    // Wallpaper Engine settings stub for compatibility
    window.wallpaperPropertyListener = {
        applyUserProperties: (props) => {},
        setPaused: function(isPaused) {}
    };

    introAnimation = true;
    spoilerChar = true; 

    textbox = document.getElementById("textbox");
    canvas = document.getElementById("canvas");
    if (!canvas) {
        console.error("[ARONA] Canvas element not found!");
        return;
    }

    // Force canvas parsing
    canvas.width = canvas.clientWidth || 800;
    canvas.height = canvas.clientHeight || 600;
    console.log("[ARONA] Canvas found. Dimensions:", canvas.width, canvas.height);

    let config = { alpha: false };
    gl = canvas.getContext("webgl", config) || canvas.getContext("experimental-webgl", config);
    if (!gl) {
        console.error("[ARONA] WebGL context unavailable.");
        return;
    }

    // Explicitly check window.spine to ensure global scope access
    if (!window.spine || !window.spine.webgl) {
        console.error("[ARONA] Spine WebGL Runtime not loaded properly. Ensure spine-webgl.js is loaded.");
        return;
    }

    try {
        // Initialize mvp matrix here after spine is loaded
        mvp = new spine.webgl.Matrix4();
        shader = spine.webgl.Shader.newTwoColoredTextured(gl);
        batcher = new spine.webgl.PolygonBatcher(gl);
        mvp.ortho2d(0, 0, canvas.width - 1, canvas.height - 1);
        skeletonRenderer = new spine.webgl.SkeletonRenderer(gl);
        assetManager = new spine.webgl.AssetManager(gl);
        
        console.log("[ARONA] Managers initialized. Loading...");

        assetManager.loadBinary(BINARY_PATH);
        assetManager.loadTextureAtlas(ATLAS_PATH);
        assetManager.loadBinary(BINARY_PATH_2);
        assetManager.loadTextureAtlas(ATLAS_PATH_2);
        assetManager.loadBinary(BINARY_PATH_BG_DAY);
        assetManager.loadTextureAtlas(ATLAS_PATH_BG_DAY);
        assetManager.loadBinary(BINARY_PATH_BG_NIGHT);
        assetManager.loadTextureAtlas(ATLAS_PATH_BG_NIGHT);

        requestAnimationFrame(load);
        
        // Add dynamic resize listener to keep elements synced
        window.addEventListener('resize', () => {
            resize();
            updateTextboxPosition();
        });

    } catch (e) {
        console.error("[ARONA] Init Error:", e);
    }
}

// Determine whether to use Plana or not
function loadoutSelect() {
	let t = new Date();
	let hr = t.getHours();
	if(forcedTime == -2) {
		hr = Math.floor(Math.random() * 24);
	}
	else if (forcedTime != -1) {
		hr = forcedTime;
	}

	LOADOUT.isday = !((spoilerChar) && hr < 6 || hr >= 18);
	LOADOUT.start = LOADOUT.isday ? Math.floor(Math.random() * 3) : Math.floor(Math.random() * 4);
	LOADOUT.start2 = Math.floor(Math.random() * 2);
	LOADOUT.introAudio = LOADOUT.isday ? INTRO_AUDIO_A : INTRO_AUDIO_P;
	LOADOUT.startAudio = LOADOUT.isday ? INTRO_STARTWORK_A : INTRO_STARTWORK_P;
	LOADOUT.interactAudio = LOADOUT.isday ? INTERACT_AUDIO_A : INTERACT_AUDIO_P;
	// LOADOUT.specialAudio = LOADOUT.isday ? SPECIAL_AUDIO_A : SPECIAL_AUDIO_P;
}

// CITATION: http://esotericsoftware.com/spine-api-reference#
// CITATION: http://en.esotericsoftware.com/forum/Spine-Unity-Making-the-arm-follow-the-mouse-7856
function interactionLoad() {
	// Touch_Point and Touch_Eye
	TPoint = spineDataA.skeleton.findBone('Touch_Point');
	TEye = spineDataA.skeleton.findBone('Touch_Eye');
	PPointX = TPoint.x;
	PPointY = TPoint.y;
	EPointX = TEye.x;
	EPointY = TEye.y;

	downaction = canvas.addEventListener('mousedown', function(event) {
		if (!acceptingClick) {
			return;
		}
		acceptingClick = false;
		let mouseData = setMouse(event);
		pressedMouse(mouseData.x, mouseData.y);
	});
	upaction = canvas.addEventListener('mouseup', function(event) {
		let mouseData = setMouse(event);
		releasedMouse(mouseData.x, mouseData.y);
	});
	moveaction = canvas.addEventListener('mousemove', function(event) {
		let mouseData = setMouse(event);
		movedMouse(mouseData.x, mouseData.y, (event.movementX * mouseData.m), event.movementY);
	});

	return 1;
}

function introLine() {
	spineDataBG.state.setAnimation(0, 'Idle_background_00', true);
	spineDataBG.state.addAnimation(1, `Idle_0${LOADOUT.start}`, true, 0);

	let array = LOADOUT.introAudio[LOADOUT.start];
	let selection = Math.floor(Math.random() * array.in.length);

	// edge case for Arona in Plana sitting state
	if (!LOADOUT.isday && LOADOUT.start == 1 && LOADOUT.start2 == 1) {
		spineDataBG.state.addAnimation(4, 'Idle_11', true, 0);

		introTrack = playLine(
			{ filepath: LOADOUT.introAudio[4].in[0], dialog: LOADOUT.introAudio[4].in_dialog[0], dPositions: LOADOUT.introAudio[4].text_location, dSequence: LOADOUT.introAudio[4].in_speaker[0] },
			function() {
				if (enableIdleLines) introLoop = setInterval(idleLines, 15000);
			}
		)

		return;
	}

	introTrack = playLine(
		{ filepath: array.in[selection], dialog: array.in_dialog[selection], dPositions: array.text_location, dSequence: array.in_speaker[selection] },
		function() {
			if (enableIdleLines) introLoop = setInterval(idleLines, 15000);
		}
	)

	if (LOADOUT.isday && LOADOUT.start == 0 && spoilerChar) {
		spineDataBG.state.addAnimation(4, `Idle_1${(LOADOUT.start2 + 1)}`, true, 0);
		introTrack.addEventListener('ended', function() {
			setTimeout(function() {
				sideTrack = playLine(
					{ filepath: SPOILER_INTRO_AUDIO[LOADOUT.start2].in[selection], dialog: SPOILER_INTRO_AUDIO[LOADOUT.start2].in_dialog[selection], dPositions: SPOILER_INTRO_AUDIO[LOADOUT.start2].text_location, dSequence: SPOILER_INTRO_AUDIO[LOADOUT.start2].in_speaker[selection] }
				)
			}, 500);
		})
	}
}

function load() {
    if (!isRunning) return;
	// Wait until the AssetManager has loaded all resources, then load the skeletons.
	if (assetManager.isLoadingComplete() && typeof introAnimation !== 'undefined') {
		canvas.width = window.innerWidth;
		canvas.height = window.innerHeight;

		loadoutSelect();

		if (!LOADOUT.isday && spoilerChar) {
			spineDataA = loadSpineData(ATLAS_PATH_2, BINARY_PATH_2, false);
			spineDataBG = loadSpineData(ATLAS_PATH_BG_NIGHT, BINARY_PATH_BG_NIGHT, false);
		}
		else {
			spineDataA = loadSpineData(ATLAS_PATH, BINARY_PATH, false);
			spineDataBG = loadSpineData(ATLAS_PATH_BG_DAY, BINARY_PATH_BG_DAY, false);
		}

		resize();
		interactionLoad();

		if (introAnimation) introLine();
		else {
			spineDataBG.state.setAnimation(0, 'Idle_background_00', true);
			spineDataBG.state.setEmptyAnimation(1, 0);
			spineDataBG.state.setEmptyAnimation(2, 0);

			spineDataA.state.setAnimation(0, 'Idle_01', true);
			alerted = true;
		}

		acceptingClick = true;

		// Plays BGM (if set)
		bgm = new Audio(bgmfile);
		bgm.volume = bgmvolume;
		bgm.play();
		bgm.addEventListener('ended', function() {
			this.currentTime = 0;
			this.play();
		}, false);

		lastFrameTime = Date.now() / 1000;
		requestAnimationFrame(render); // Loading is done, call render every frame.
	} else {
		requestAnimationFrame(load);
	}
}

function loadSpineData(a, b, premultipliedAlpha) {
	// Load the texture atlas from the AssetManager.
	let atlas = assetManager.get(a);

	// Create a AtlasAttachmentLoader that resolves region, mesh, boundingbox and path attachments
	let atlasLoader = new spine.AtlasAttachmentLoader(atlas);

	// Create a SkeletonBinary instance for parsing the .skel file.
	let skeletonBinary = new spine.SkeletonBinary(atlasLoader);

	// Set the scale to apply during parsing, parse the file, and create a new skeleton.
	skeletonBinary.scale = 1;
	let skeletonData = skeletonBinary.readSkeletonData(assetManager.get(b));
	let skeleton = new spine.Skeleton(skeletonData);
	let bounds = calculateSetupPoseBounds(skeleton);

	// Create an AnimationState, and set the initial animation in looping mode.
	let animationStateData = new spine.AnimationStateData(skeleton.data);
	animationStateData.defaultMix = 0.5;
	let animationState = new spine.AnimationState(animationStateData);

	// Pack everything up and return to caller.
	return { skeleton: skeleton, state: animationState, bounds: bounds, premultipliedAlpha: premultipliedAlpha };
}

function calculateSetupPoseBounds(skeleton) {
	skeleton.setToSetupPose();
	skeleton.updateWorldTransform();
	let offset = new spine.Vector2();
	let size = new spine.Vector2();
	skeleton.getBounds(offset, size, []);
	return { offset: offset, size: size };
}

function render() {
    if (!isRunning) return;
    try {
	let now = Date.now() / 1000;
	let delta = now - lastFrameTime;

	lastFrameTime = now;

	gl.clearColor(bufferColor[0], bufferColor[1], bufferColor[2], 1);
	gl.clear(gl.COLOR_BUFFER_BIT);

	// Apply the animation state based on the delta time.
	let skeleton = spineDataBG.skeleton;
	let state = spineDataBG.state;
	let premultipliedAlpha = spineDataBG.premultipliedAlpha;
	state.update(delta);
	state.apply(skeleton);
	skeleton.updateWorldTransform();

	// Bind the shader and set the texture and model-view-projection matrix.
	shader.bind();
	shader.setUniformi(spine.webgl.Shader.SAMPLER, 0);
	shader.setUniform4x4f(spine.webgl.Shader.MVP_MATRIX, mvp.values);

	// Start the batch and tell the SkeletonRenderer to render the active skeleton.
	batcher.begin(shader);

	skeletonRenderer.premultipliedAlpha = premultipliedAlpha;
	skeletonRenderer.draw(batcher, skeleton);
	if (alerted) {
		let skeleton2 = spineDataA.skeleton;
		let state2 = spineDataA.state;
		skeleton2.x = characterOffset.x;
		skeleton2.y = characterOffset.y;
		state2.update(delta);
		state2.apply(skeleton2);
		skeleton2.updateWorldTransform();
		skeletonRenderer.draw(batcher, skeleton2);
	};
	batcher.end();

	shader.unbind();

	// throttle fps
	let elapsed = Date.now() / 1000 - now;
	let targetFrameTime = 1 / targetFps;
	let delay = Math.max(targetFrameTime - elapsed, 0) * 1000;

	setTimeout(() => {
		requestAnimationFrame(render);
	}, delay);
    } catch (e) {
        console.error("[ARONA] Render Error:", e);
        isRunning = false;
    }
}

function resize() {
	let w = canvas.clientWidth;
	let h = canvas.clientHeight;
	if (canvas.width != w || canvas.height != h) {
		canvas.width = w;
		canvas.height = h;
	}

	// Calculations to center the skeleton in the canvas.
	let centerX = 0;
	let centerY = 900;
	let wr = canvas.width / 2880;
	let hr = canvas.height / 1620;
	let width = (2880 / customScale);
	let height = (1620 / customScale);

	if (wr < hr) {
		width = height * (canvas.width / canvas.height);

		transpose = 1620 / canvas.height;
	}
	else if (wr > hr) {
		height = width * (canvas.height / canvas.width);

		transpose = 2880 / canvas.width;
	}
	else {
		transpose = 1620 / canvas.height;
	}

	mvp.ortho2d(centerX - width / 2, centerY - height / 2, width, height);
    if (gl) gl.viewport(0, 0, canvas.width, canvas.height);
    
    if (DEBUG_HITBOX) drawDebugHitboxes();
}

function drawDebugHitboxes() {
    // Remove existing debug elements
    const existing = document.querySelectorAll('.debug-hitbox');
    existing.forEach(el => el.remove());

    const colors = {
        headpat: 'rgba(255, 0, 0, 0.3)',
        face: 'rgba(0, 255, 0, 0.3)',
        mouth: 'rgba(0, 255, 255, 0.3)',
        chest: 'rgba(0, 0, 255, 0.3)',
        skirt: 'rgba(255, 255, 0, 0.3)'
    };

    for (let key in HITBOX) {
        const box = HITBOX[key];
        const rect = document.createElement('div');
        rect.className = 'debug-hitbox';
        rect.style.position = 'absolute';
        rect.style.border = '2px solid white';
        rect.style.backgroundColor = colors[key] || 'rgba(255, 255, 255, 0.3)';
        rect.style.pointerEvents = 'none'; // Click through
        rect.style.zIndex = '9999';
        
        // Convert coords
        // logical X (0-2880) -> Screen X
        // tInvert(n, 'x')
        const x1 = tInvert(box.xMin + characterOffset.x, 'x');
        const x2 = tInvert(box.xMax + characterOffset.x, 'x');
        const y1 = tInvert(box.yMin - characterOffset.y, 'y'); // y is inverted in some systems? Let's check tInvert logic.
        // tInvert maps standard axis? 
        // In pressedMouse: ty = t(y, 'y'). and checks ty > yMin && ty < yMax.
        // So ty is consistent with yMin/yMax.
        // tInvert is the inverse.
        
        const yTop = tInvert(box.yMin - characterOffset.y, 'y');
        const yBottom = tInvert(box.yMax - characterOffset.y, 'y');

        // Check orientation of tInvert (does 0 map to top or bottom?)
        // Canvas usually 0 is top.
        // If tInvert maps perfectly, then:
        rect.style.left = Math.min(x1, x2) + 'px';
        rect.style.top = Math.min(yTop, yBottom) + 'px';
        rect.style.width = Math.abs(x2 - x1) + 'px';
        rect.style.height = Math.abs(yBottom - yTop) + 'px';
        
        // Label
        rect.innerText = key;
        rect.style.color = 'white';
        rect.style.fontSize = '12px';
        rect.style.fontWeight = 'bold';
        rect.style.textShadow = '1px 1px 0 #000';

        document.body.appendChild(rect);
    }
}

window.stopAronaEngine = function() {
    console.log("[ARONA] Stopping engine...");
    isRunning = false;

    // Reset State Flags
    alerted = false;
    mouseSelect = -1;
    globalPause = false;
    acceptingClick = false;
    
    // Stop Audio
    if (bgm) { 
        bgm.pause(); 
        bgm = null; 
    }
    if (voiceAudio) {
        voiceAudio.pause();
        voiceAudio = null;
    }
    if (introTrack) {
        introTrack.pause();
        introTrack = null;
    }
    if (sideTrack) {
        sideTrack.pause();
        sideTrack = null;
    }

    // Clear Logic Loops
    if (introLoop) {
        clearInterval(introLoop);
        introLoop = null;
    }
    if (trackerID) {
        clearInterval(trackerID);
        trackerID = -1;
    }
    if (untrackerID) {
        clearInterval(untrackerID);
        untrackerID = -1;
    }
    if (unpetID) {
        clearInterval(unpetID);
        unpetID = -1;
    }

    // Reset Spine & WebGL Data to prevent ghosting on re-init
    spineDataA = null;
    spineDataBG = null;
    skeletonRenderer = null;
    assetManager = null;
    batcher = null;
    shader = null;
    
    // Unbind events (optional, but good practice if listeners were named)
    // Since listeners are anonymous in init(), we can't remove them easily
    // without cloning the element, but stopping the logic loop is usually enough.
};

window.startAronaEngine = function() {
    console.log("[ARONA] Window.startAronaEngine called.");
    window.stopAronaEngine(); // Ensure clean slate
    // Small delay to ensure loop has stopped
    setTimeout(init, 50);
};
