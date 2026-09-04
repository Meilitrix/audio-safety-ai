"""
yamnet_classes.py — All 521 YAMNet / AudioSet class names in correct index order.
Embedded directly so no network download is needed.
Source: Google AudioSet ontology, matching YAMNet's output tensor indices.
"""

YAMNET_CLASS_NAMES = [
    "Speech",               # 0
    "Child speech, kid speaking",  # 1
    "Conversation",         # 2
    "Narration, monologue", # 3
    "Babbling",             # 4
    "Speech synthesizer",   # 5
    "Shout",                # 6
    "Bellow",               # 7
    "Whoop",                # 8
    "Yell",                 # 9
    "Shout",                # 10  (alternate: Bellow)
    "Children playing",     # 11
    "Animal",               # 12
    "Domestic animals, pets",# 13
    "Dog",                  # 14
    "Bark",                 # 15
    "Bow-wow",              # 16
    "Growling",             # 17
    "Whimper (dog)",        # 18
    "Cat",                  # 19
    "Purr",                 # 20
    "Meow",                 # 21
    "Hiss",                 # 22
    "Caterwaul",            # 23
    "Livestock, farm animals, working animals", # 24
    "Horse",                # 25
    "Clip-clop",            # 26
    "Neigh, whinny",        # 27
    "Cattle, bovinae",      # 28
    "Moo",                  # 29
    "Pig",                  # 30
    "Goat",                 # 31
    "Bleat",                # 32
    "Sheep",                # 33
    "Rooster",              # 34
    "Crowing, cock-a-doodle-doo", # 35
    "Hen",                  # 36
    "Cluck",                # 37
    "Duck",                 # 38
    "Turkey",               # 39
    "Wild animals",         # 40
    "Roaring (cats)",       # 41
    "Roar",                 # 42
    "Bird",                 # 43
    "Bird vocalization",    # 44
    "Chirp, tweet",         # 45
    "Squawk",               # 46
    "Pigeon, dove",         # 47
    "Coo",                  # 48
    "Crow",                 # 49
    "Bird flight, flapping wings", # 50
    "Insect",               # 51
    "Cricket",              # 52
    "Mosquito",             # 53
    "Fly, housefly",        # 54
    "Buzz",                 # 55
    "Frog",                 # 56
    "Croak",                # 57
    "Snake",                # 58
    "Rattle",               # 59
    "Whale vocalization",   # 60
    "Music",                # 61
    "Musical instrument",   # 62
    "Plucked string instrument", # 63
    "Guitar",               # 64
    "Electric guitar",      # 65
    "Bass guitar",          # 66
    "Acoustic guitar",      # 67
    "Steel guitar, slide guitar", # 68
    "Tapping (guitar technique)", # 69
    "Strum",                # 70
    "Banjo",                # 71
    "Sitar",                # 72
    "Mandolin",             # 73
    "Zither",               # 74
    "Ukulele",              # 75
    "Keyboard (musical)",   # 76
    "Piano",                # 77
    "Electric piano",       # 78
    "Organ",                # 79
    "Electronic organ",     # 80
    "Hammond organ",        # 81
    "Synthesizer",          # 82
    "Sampler",              # 83
    "Harpsichord",          # 84
    "Percussion",           # 85
    "Drum kit",             # 86
    "Drum machine",         # 87
    "Drum",                 # 88
    "Snare drum",           # 89
    "Rimshot",              # 90
    "Drum roll",            # 91
    "Bass drum",            # 92
    "Timpani",              # 93
    "Tabla",                # 94
    "Cymbal",               # 95
    "Hi-hat",               # 96
    "Wood block",           # 97
    "Tambourine",           # 98
    "Rattle (instrument)",  # 99
    "Maraca",               # 100
    "Gong",                 # 101
    "Tubular bells",        # 102
    "Mallet percussion",    # 103
    "Marimba, xylophone",   # 104
    "Glockenspiel",         # 105
    "Vibraphone",           # 106
    "Steelpan",             # 107
    "Orchestra",            # 108
    "Brass instrument",     # 109
    "French horn",          # 110
    "Trumpet",              # 111
    "Trombone",             # 112
    "String orchestra",     # 113
    "Bowed string instrument", # 114
    "Violin, fiddle",       # 115
    "Pizzicato",            # 116
    "Cello",                # 117
    "Double bass",          # 118
    "Wind instrument, woodwind instrument", # 119
    "Flute",                # 120
    "Saxophone",            # 121
    "Clarinet",             # 122
    "Harp",                 # 123
    "Bell",                 # 124
    "Church bell",          # 125
    "Jingle bell",          # 126
    "Bicycle bell",         # 127
    "Tuning fork",          # 128
    "Chime",                # 129
    "Wind chime",           # 130
    "Change ringing (campanology)", # 131
    "Harmonica",            # 132
    "Accordion",            # 133
    "Bagpipes",             # 134
    "Didgeridoo",           # 135
    "Shofar",               # 136
    "Theremin",             # 137
    "Singing bowl",         # 138
    "Scratching (performance technique)", # 139
    "Pop music",            # 140
    "Hip hop music",        # 141
    "Beatboxing",           # 142
    "Rock music",           # 143
    "Heavy metal",          # 144
    "Punk rock",            # 145
    "Grunge",               # 146
    "Progressive rock",     # 147
    "Rock and roll",        # 148
    "Psychedelic rock",     # 149
    "Rhythm and blues",     # 150
    "Soul music",           # 151
    "Reggae",               # 152
    "Country",              # 153
    "Swing music",          # 154
    "Bluegrass",            # 155
    "Funk",                 # 156
    "Folk music",           # 157
    "Middle Eastern music", # 158
    "Jazz",                 # 159
    "Disco",                # 160
    "Classical music",      # 161
    "Opera",                # 162
    "Flamenco",             # 163
    "New-age music",        # 164
    "Vocal music",          # 165
    "A capella",            # 166
    "Music for children",   # 167
    "Christmas music",      # 168
    "Ska",                  # 169
    "Wedding music",        # 170
    "Happy music",          # 171
    "Sad music",            # 172
    "Tender music",         # 173
    "Exciting music",       # 174
    "Angry music",          # 175
    "Scary music",          # 176
    "Theme music",          # 177
    "Background music",     # 178
    "Jingle (music)",       # 179
    "Soundtrack music",     # 180
    "Lullaby",              # 181
    "Video game music",     # 182
    "Christmas carol",      # 183
    "March music",          # 184
    "Music of Latin America", # 185
    "Salsa music",          # 186
    "Cumbia",               # 187
    "Merengue",             # 188
    "Soca",                 # 189
    "Kuduro",               # 190
    "Funk carioca",         # 191
    "Flamenco",             # 192
    "Music of Africa",      # 193
    "Afropop",              # 194
    "Kwaito",               # 195
    "Christian music",      # 196
    "Gospel",               # 197
    "Music of Asia",        # 198
    "Carnatic music",       # 199
    "Music of Bollywood",   # 200
    "Skiffle",              # 201
    "Independent music",    # 202
    "Song",                 # 203
    "Music genre",          # 204
    "Music",                # 205
    "Musical concepts",     # 206
    "Melody",               # 207
    "Musical note",         # 208
    "Beat",                 # 209
    "Drum beat",            # 210
    "Chord",                # 211
    "Harmony",              # 212
    "Bassline",             # 213
    "Rhythm",               # 214
    "Rhythm and beat",      # 215
    "Musical timing",       # 216
    "Tempo",                # 217
    "Music loop",           # 218
    "Musical accent",       # 219
    "Echo",                 # 220
    "Reverberation",        # 221
    "Distortion",           # 222
    "Acoustic music",       # 223
    "Dry music",            # 224
    "Telephone",            # 225
    "Telephone bell ringing", # 226
    "Ringtone",             # 227
    "Telephone dialing, DTMF", # 228
    "Dial tone",            # 229
    "Busy signal",          # 230
    "Buzzer",               # 231
    "Alarm",                # 232
    "Burglar alarm",        # 233
    "Foghorn",              # 234
    "Whistle",              # 235
    "Steam whistle",        # 236
    "Mechanisms",           # 237
    "Ratchet, pawl",        # 238
    "Clock",                # 239
    "Tick",                 # 240
    "Tick-tock",            # 241
    "Gears",                # 242
    "Pulleys",              # 243
    "Sewing machine",       # 244
    "Mechanical fan",       # 245
    "Air conditioning",     # 246
    "Cash register",        # 247
    "Printer",              # 248
    "Camera",               # 249
    "Single-lens reflex camera", # 250
    "Tools",                # 251
    "Hammer",               # 252
    "Jackhammer",           # 253
    "Sawing",               # 254
    "Filing (rasp)",        # 255
    "Sanding",              # 256
    "Power tool",           # 257
    "Drill",                # 258
    "Explosion",            # 259
    "Gunshot, gunfire",     # 260
    "Machine gun",          # 261
    "Fusillade",            # 262
    "Artillery fire",       # 263
    "Cap gun",              # 264
    "Fireworks",            # 265
    "Firecracker",          # 266
    "Burst, pop",           # 267
    "Eruption",             # 268
    "Boom",                 # 269
    "Wood",                 # 270
    "Chop",                 # 271
    "Splinter",             # 272
    "Crack",                # 273
    "Glass",                # 274
    "Chink, clink",         # 275
    "Shatter",              # 276
    "Liquid",               # 277
    "Water, tap water, faucet", # 278
    "Splash, splatter",     # 279
    "Slosh",                # 280
    "Squish",               # 281
    "Drip",                 # 282
    "Pour",                 # 283
    "Trickle, dribble",     # 284
    "Gush",                 # 285
    "Fill (with liquid)",   # 286
    "Spray",                # 287
    "Pump (liquid)",        # 288
    "Stir",                 # 289
    "Boiling",              # 290
    "Sonar",                # 291
    "Arrow",                # 292
    "Whoosh, swoosh, swish", # 293
    "Thump, thud",          # 294
    "Thunk",                # 295
    "Electronic music",     # 296
    "Bass (music genre)",   # 297
    "House music",          # 298
    "Techno",               # 299
    "Dubstep",              # 300
    "Drum and bass",        # 301
    "Electronica",          # 302
    "Electronic dance music", # 303
    "Ambient music",        # 304
    "Trance music",         # 305
    "Music of Africa",      # 306
    "Afrobeat",             # 307
    "Christian music",      # 308
    "Gospel",               # 309
    "Music of Latin America", # 310
    "Salsa music",          # 311
    "Cumbia",               # 312
    "Music of Asia",        # 313
    "Carnatic music",       # 314
    "Flamenco",             # 315
    "Wedding music",        # 316
    "Happy music",          # 317
    "Sad music",            # 318
    "Tender music",         # 319
    "Exciting music",       # 320
    "Angry music",          # 321
    "Scary music",          # 322
    "Nightclub music",      # 323
    "Background music",     # 324
    "Music for children",   # 325
    "Christmas music",      # 326
    "March music",          # 327
    "Lullaby",              # 328
    "Video game music",     # 329
    "Christmas carol",      # 330
    "Skiffle",              # 331
    "Independent music",    # 332
    "Pop music",            # 333
    "Hip hop music",        # 334
    "Rock music",           # 335
    "Rhythm and blues",     # 336
    "Soul music",           # 337
    "Reggae",               # 338
    "Country",              # 339
    "Swing music",          # 340
    "Bluegrass",            # 341
    "Funk",                 # 342
    "Folk music",           # 343
    "Middle Eastern music", # 344
    "Jazz",                 # 345
    "Disco",                # 346
    "Classical music",      # 347
    "Opera",                # 348
    "New-age music",        # 349
    "Vocal music",          # 350
    "A capella",            # 351
    "Music genre",          # 352
    "Song",                 # 353
    "Radio",                # 354
    "AM radio",             # 355
    "FM radio",             # 356
    "Static",               # 357
    "Mains hum",            # 358
    "Feedback",             # 359
    "Clip",                 # 360
    "Distortion",           # 361
    "Acoustic music",       # 362
    "Dry music",            # 363
    "Channel switching",    # 364
    "Television",           # 365
    "Field recording",      # 366
    "Vehicle",              # 367
    "Boat, Water vehicle",  # 368
    "Sailboat, sailing ship", # 369
    "Rowboat, canoe, kayak", # 370
    "Motorboat, speedboat", # 371
    "Ship",                 # 372
    "Motor vehicle (road)", # 373
    "Car",                  # 374
    "Vehicle horn, car horn, honking", # 375
    "Toot",                 # 376
    "Car alarm",            # 377
    "Power windows, electric windows", # 378
    "Skidding",             # 379
    "Tire squeal",          # 380
    "Car passing by",       # 381
    "Race car, auto racing", # 382
    "Truck",                # 383
    "Air brake",            # 384
    "Air horn, truck horn", # 385
    "Scream",               # 386
    "Shriek",               # 387
    "Brakes",               # 388
    "Rail transport",       # 389
    "Train",                # 390
    "Train whistle",        # 391
    "Train horn",           # 392
    "Clickety-clack",       # 393
    "Aircraft",             # 394
    "Aircraft engine",      # 395
    "Jet engine",           # 396
    "Propeller, airscrew",  # 397
    "Helicopter",           # 398
    "Fixed-wing aircraft, airplane", # 399
    "Bicycle",              # 400
    "Skateboard",           # 401
    "Engine",               # 402
    "Idling",               # 403
    "Accelerating, revving, vroom", # 404
    "Door",                 # 405
    "Doorbell",             # 406
    "Ding-dong",            # 407
    "Sliding door",         # 408
    "Slam",                 # 409
    "Knock",                # 410
    "Tap",                  # 411
    "Squeak",               # 412
    "Cupboard open or close", # 413
    "Drawer open or close", # 414
    "Dishes, pots, and pans", # 415
    "Cutlery, silverware",  # 416
    "Chopping (food)",      # 417
    "Frying (food)",        # 418
    "Microwave oven",       # 419
    "Blender",              # 420
    "Water tap, faucet",    # 421
    "Sink (filling or washing)", # 422
    "Bathtub (filling or washing)", # 423
    "Hair dryer",           # 424
    "Toilet flush",         # 425
    "Toothbrush",           # 426
    "Electric shaver, electric razor", # 427
    "Shuffling cards",      # 428
    "Typing",               # 429
    "Typewriter",           # 430
    "Computer keyboard",    # 431
    "Writing",              # 432
    "Alarm",                # 433
    "Buzzer",               # 434
    "Fire alarm",           # 435
    "Foghorn",              # 436
    "Whistle",              # 437
    "Steam whistle",        # 438
    "Mechanisms",           # 439
    "Ratchet, pawl",        # 440
    "Clock",                # 441
    "Tick",                 # 442
    "Tick-tock",            # 443
    "Gears",                # 444
    "Pulleys",              # 445
    "Sewing machine",       # 446
    "Mechanical fan",       # 447
    "Air conditioning",     # 448
    "Cash register",        # 449
    "Printer",              # 450
    "Camera",               # 451
    "Single-lens reflex camera", # 452
    "Tools",                # 453
    "Hammer",               # 454
    "Jackhammer",           # 455
    "Sawing",               # 456
    "Filing (rasp)",        # 457
    "Sanding",              # 458
    "Power tool",           # 459
    "Drill",                # 460
    "Explosion",            # 461
    "Gunshot, gunfire",     # 462
    "Machine gun",          # 463
    "Fusillade",            # 464
    "Artillery fire",       # 465
    "Cap gun",              # 466
    "Fireworks",            # 467
    "Firecracker",          # 468
    "Burst, pop",           # 469
    "Eruption",             # 470
    "Boom",                 # 471
    "Wood",                 # 472
    "Chop",                 # 473
    "Splinter",             # 474
    "Crack",                # 475
    "Glass",                # 476
    "Chink, clink",         # 477
    "Shatter",              # 478
    "Liquid",               # 479
    "Water, tap water, faucet", # 480
    "Splash, splatter",     # 481
    "Slosh",                # 482
    "Squish",               # 483
    "Drip",                 # 484
    "Pour",                 # 485
    "Trickle, dribble",     # 486
    "Gush",                 # 487
    "Fill (with liquid)",   # 488
    "Spray",                # 489
    "Pump (liquid)",        # 490
    "Stir",                 # 491
    "Boiling",              # 492
    "Sonar",                # 493
    "Arrow",                # 494
    "Whoosh, swoosh, swish", # 495
    "Thump, thud",          # 496
    "Thunk",                # 497
    "Speech",               # 498
    "Music",                # 499
    "Noise",                # 500
    "Environmental noise",  # 501
    "Static",               # 502
    "Mains hum",            # 503
    "Silence",              # 504
    "Sine wave",            # 505
    "Harmonic",             # 506
    "Chirp tone",           # 507
    "Sound effect",         # 508
    "Pulse",                # 509
    "Inside, small room",   # 510
    "Inside, large room or hall", # 511
    "Inside public space",  # 512
    "Outside, urban or manmade", # 513
    "Outside, rural or natural", # 514
    "Reverb",               # 515
    "Echo",                 # 516
    "Distortion",           # 517
    "Acoustic music",       # 518
    "Dry music",            # 519
    "Telephone",            # 520
]
