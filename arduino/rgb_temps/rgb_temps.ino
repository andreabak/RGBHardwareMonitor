#include "lights.h"


// TODO: Consider possibility to enable debug at runtime (make it a function instead?)
#define DEBUG

#ifdef DEBUG
    #include "serial_printf.h"
    #define DEBUG_PRINT(fmt, ...)  serial_printf((Serial), (fmt "\n"), ##__VA_ARGS__)
#else
    #define DEBUG_PRINT(fmt, ...)
#endif



/* ------------------------------- CONSTANTS ------------------------------- */


#define CMD_BUFFER_SIZE  32
#define CMD_DELIMITERS   " "

// TODO: Consider allowing to set these parameters directly from python config (serial resets on connection anyways)
const uint8_t ringsCount = 2;
RingLights* rings[ringsCount];

void setupRings() {
    rings[0] = new RingLights(2, 16, DEFAULT_STRIP_TYPE);
    rings[1] = new RingLights(4, 13, DEFAULT_STRIP_TYPE);
}



/* ------------------------------- MAIN CODE ------------------------------- */


uint8_t mode = 1;
const unsigned int readDelay = 1;

unsigned long lastus = micros();
float fps = 0.0;
float fpsAvg = 0.0;
const float fpsAvgSamples = 300.0;

void setup() {
    Serial.begin(115200);
    Serial.setTimeout(readDelay);
    setupRings();
}

void flushSerialInput() {
    while (Serial.available())
        Serial.read();
}

// TODO: Improve commands validation (some values get out of sync / go to zero sometimes)
void parseCommand(char* cmdBuffer) {  // TODO: Implement commands to set custom colors, then save in Flash/EEPROM
    char cmd = NULL;
    uint8_t ringId, rawHeat, rawLoad, rawRpm;

    uint8_t cmdPartNum = 0;
    char* cmdPart = strtok(cmdBuffer, CMD_DELIMITERS);
    while (cmdPart != NULL) {
        if (!cmdPartNum)
            cmd = cmdPart[0];
        else {
            if (cmd == 'H') {
                // Does not accept args for now
            } else if (cmd == 'U') {
                int val = atoi(cmdPart);
                switch (cmdPartNum) {
                    case 1: ringId = val; break;
                    case 2: rawHeat = val; break;
                    case 3: rawLoad = val; break;
                    case 4: rawRpm = val; break;
                }
            } else {
                DEBUG_PRINT("Invalid command: %c", cmd);
                return;  // Stop parsing
            }
        }
        cmdPart = strtok(NULL, CMD_DELIMITERS);
        cmdPartNum++;
    }
    if (!cmdPartNum) {
        DEBUG_PRINT("Received empty input");
        return;  // Stop parsing
    }

    auto check_args_num = [cmd, cmdPartNum](uint8_t expectedNumArgs) -> bool {
        if ((cmdPartNum - 1) != expectedNumArgs) {
            DEBUG_PRINT("Invalid arguments length for command %c (given %d, expected %d)",
                        cmd, cmdPartNum - 1, expectedNumArgs);
            return false;
        }
        return true;
    };

    if (cmd == 'H') {
        if (!check_args_num(0))
            return;
        Serial.println("EHLO RGBHardwareMonitor");
    } else if (cmd == 'U') {
        if (!check_args_num(4))
            return;
        if (!ringId || ringId > ringsCount) {
            DEBUG_PRINT("Invalid ring id: %d", ringId);
        } else {
            float inHeat = max(0.0, min(1.0, (rawHeat / 255.0)));
            float inLoad = max(0.0, min(1.0, (rawLoad / 255.0)));
            float inRpm  = max(0.0, min(1.0, (rawRpm / 255.0)));
            DEBUG_PRINT("Parsed input (mode: %d, ring: %d, heat: %f, load: %f, rpm: %f)",
                        mode, ringId, inHeat, inLoad, inRpm);
            rings[ringId-1]->setSensors(inHeat, inLoad, inRpm);
        }
    } else {
        DEBUG_PRINT("Invalid command: %c", cmd);
    }
    DEBUG_PRINT("Current fps: %f, average fps: %f", fps, fpsAvg);
}

void loop() {
    if (Serial.available()) {
        char cmdBuffer[CMD_BUFFER_SIZE+1];
        Serial.setTimeout(100);  // Set timeout to long wait to make sure all data is received (should only take 1ms tho)
        uint8_t readBytes = Serial.readBytesUntil('\n', cmdBuffer, CMD_BUFFER_SIZE);
        Serial.setTimeout(readDelay);
        cmdBuffer[readBytes] = NULL;
        parseCommand(cmdBuffer);
        flushSerialInput();
    }
    for (uint8_t i=0; i<ringsCount; i++) {
        rings[i]->loopStep();
        if (fpsAvg)
            rings[i]->setFps(fpsAvg);
    }
    unsigned long currus = micros();
    fps = 1000000.0 / (currus - lastus);
    if (!fpsAvg)
        fpsAvg = fps;
    else
        fpsAvg = mixValues(fpsAvg, fps, 1.0 / fpsAvgSamples);
    lastus = currus;
}
