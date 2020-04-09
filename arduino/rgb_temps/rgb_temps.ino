#include "lights.h"



/* ------------------------------- CONSTANTS ------------------------------- */


const uint8_t ringsCount = 1;
RingLights* rings[ringsCount];

void setupRings() {
    rings[0] = new RingLights(3, 16, DEFAULT_STRIP_TYPE);
}



/* ------------------------------- MAIN CODE ------------------------------- */


uint8_t mode = 1;
unsigned int readDelay = 1;

void setup() {
    Serial.begin(115200);
    Serial.flush();
    Serial.setTimeout(readDelay);
    setupRings();
}

void loop() {  // TODO: Implement commands to set custom colors, then save in Flash/EEPROM
    if (Serial.available()) {  // TODO: Validate input
        uint8_t rawMode = Serial.parseInt();
        if (rawMode != 0) {
            Serial.setTimeout(100);
            mode = rawMode;
            uint8_t ringId = Serial.parseInt();
            if (!ringId || ringId > ringsCount) {
                Serial.print("Invalid ring id"); Serial.println(ringId);
            } else {
                float inHeat = Serial.parseInt() / 255.0;
                float inLoad = Serial.parseInt() / 255.0;
                float inRpm  = Serial.parseInt() / 255.0;
                Serial.print("Parsed input (mode: "); Serial.print(mode);
                            Serial.print(", ring: "); Serial.print(ringId);
                            Serial.print(", heat: "); Serial.print(inHeat);
                            Serial.print(", load: "); Serial.print(inLoad);
                            Serial.print(", rpm: "); Serial.print(inRpm); Serial.println(")");
                rings[ringId-1]->setSensors(inHeat, inLoad, inRpm);
            }
            Serial.setTimeout(readDelay);
        }
    }
    for (uint8_t i=0; i<ringsCount; i++)
        rings[i]->loopStep();
}
