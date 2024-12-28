"""
This script takes in an existing MIDI file and inserts 1 measure of silence, then a count-in, to the
beginning of the song. The countin is set to use the 'RotoTom' general MIDI preset. If Jeff's'
custom countin soundfount is used on playback this will result in an actual vocal count-in.

CONFESSION: This is my first real Python program, and it shows. It's a bit of a mess as it blends
too many different styles, and is just plain messy. Nonetheless, it pretty much works.
"""
#
# COMMAND LINE: python midi-countin.py -i TestScores-and-MIDIs/Test-02_Charleston-Gals_arr01.mid -o Test-02_Charleston-Gals_arr01_OUT.mid
#
#=================================================================================================
# PROJECT: Audio: Prepend a Count-In onto existing MIDI file
# COMPONENT: midi-countin.py
#
# TODO: Preserve the input file's 'clocks-per-click' value as set in a parm of Time-Signature
#       messages.
#
# TODO: 'Harmony Chords.' Like muted tracks Musescore will always export messages for these.
#       Perplexingly, this is done as as a separate 'channel number' in the same track as the
#       the staff that the chords are attached to. IDEALLY I'd like to pull those out into their
#       own, separate, track when they are not muted, with an appropriate track-name.
#       Or remove all the messages associated with them if they are fully muted.
#
# TODO: Consider idea of merging piano staff left-hand / right-hand tracks into single track.
# =================================================================================================
#
# 12/28/2024 Jeff Rocchio:
#   ->  12-28 @ 12:52. Completed first release. Believe it all to be working, but for sure there
#                      are any number of bugs in it.
#
#       This was commit:
#

__version__ = "12-28-2024a"

import os
import sys
import argparse                     # <-- For defining and handling command line arguments.
import re                           # <-- For Regex processing (e.g., validation of string entries).
import mido                         # <-- The MIDI handling library.


# =================================================================================================
#    GLOBAL CONSTANTS
# =================================================================================================
# NOTE: Python doesn't have immutable constants. So you just define regular variables using the
#       ususal naming convention of all caps with underscores for spaces. But note they are not
#       really immutable. So be careful!

    # The set of escape sequences used for the terminal command line user interface.
CLI_CMDS = {
    "headerColWidth": 100 # TODO: Make this go away, see to-do in def listAllMessages(self):
}



class errorHandler:

    def __init__(self):
        self.errInProcess = False #     <-- True if we are currently handling an error
        self.lastErrorID = 0 #          <-- ID of the latest error.
        self.errSet = [ #               <-- Dictionary containing the set of possible errors and their fatality level.
            ("Cannot Find Input File", True),
            ("Output File Path Invalid.", True),
            ("An Error Occurred, Cannot Continue to Process: Exiting Program.", True),
            ("No Open MIDI Channel Available for CountIn Track: Exiting Program.", True)
        ]

    def set_Error(self, ID):
        """ Description: Set error condition to TRUE
        Param: self - Virtual param to errorHandler class data & methods
        Param: ID :Integer - ID number of the error being declared
        Returns: Null - there is no return value
        """
        self.lastErrorID = ID
        self.errInProcess = True

    def handleError(self):
        """ Description: Handle the current error condition, if any
        Param: self - Virtual param to errorHandler class data & methods
        Result: If no error, nothing happens. If non-fatal error display error description,
        clear error state, then exit. if fatal error display error description and exit the script.
        Returns: Null - there is no return value
        """
        if self.errInProcess:
            errIndex = self.lastErrorID - 1
            print('\n ******** ERROR *********')
            print(f'   {self.errSet[errIndex][0]} (Error ID: {self.lastErrorID})')
            if self.errSet[errIndex][1]:
                print('   --- Error Is Fatal: Exiting Program.\n')
                sys.exit(1)
            self.errInProcess = False



# =================================================================================================
#    CLASS DEFINITIONS - MODEL
# =================================================================================================

class OutputMIDI:
    """ Description: Represents output MIDI file we are creating.
    USAGE:  Intended to be fully encapsulated within the Song class. As such, other than this
            class definition, this class should not be called into directly.
    NOTE:   We are effectively subclassing mido.MidiFile here by wrapping an instance of that
            class with a few helper methods that we need.
    TODO:   Gotta figure this out.
    """

    def __init__(self, outputFile):
        self.midiOut = mido.MidiFile()
        self.outFilePath = outputFile
        self.countTrackChannel = 99 #   <-- 99 signals channel net yet set, invalid.
        self.songCurrPos = -1 #         <-- Acts as a current position 'playhead' for the output file.

    def assemble_outputMIDI(self, song):
        """ Description: Populate outputMIDI tracks from all the data we now have available
        PARAM: song - Instance of the Song class
        DOC: sd OutputMIDI.assemble_outputMIDI
        Note:  x
        TODO:  x
        """
        self.midiOut.ticks_per_beat = song.ticksPerBeat
        self._initilizeTracks(song)
        display.track_namesForFile(self.midiOut, 'Output MIDI')
        self._calcSilence(song)
        self._populateCountIn(song)
        self._populateOriginalSong(song)
        #self._populateRepeatPlays(song)
        self._closeTracks() # <-- I don't think I any longer need this function.

    def _initilizeTracks(self, song):
        """ Description: Creates output tracks and populates with minimally needed initialization
        messages
        PARAM:  song - Instance of the Song class.
        DOC: sd OutputMIDI._initilizeTracks(Song)
        """
        # Note: Notice that I am using song.trackInfo to drive the first for loop in order to
        #       handle fact that some input tracks will not be copied to OutputMIDI. This is also
        #       why I am using the outTrackIdx local variable.
        #
        #-----| Declare Local Helper Variables ----------------------------------------------------
        outTrackIdx = 0
        #
        #-----| Create OutputMIDI Tracks ----------------------------------------------------------
        for i, row in enumerate(song.trackInfo):
            if row[TI_KEEP] is True:
                self.midiOut.add_track(row[TI_NAME])
                if row[TI_KEY] != 'X':
                    self.midiOut.tracks[outTrackIdx].append(mido.MetaMessage('key_signature', key=row[TI_KEY], time=0))
                song.trackInfo[i][TI_OUTTRACKNUM] = outTrackIdx
                outTrackIdx += 1
        self.midiOut.tracks[0].append(mido.MetaMessage('time_signature', numerator=song.timeSigNum, denominator=song.timeSigDen, time=0))
        self.midiOut.tracks[0].append(mido.MetaMessage('set_tempo', tempo=song.tempoMIDI, time=0))
        self._initilize_countInitMsgs(song.countIn, self.midiOut.tracks[song.trackInfo[-1][TI_OUTTRACKNUM]])


    def _initilize_countInitMsgs(self, countIn, ctTrack):
        """ Description: A helper to _initilizeTracks(). Puts initialization messages into Count In track
        PARAM:  countIn - Instance of the CountIn class.
        PARAM:  ctTrack - The Count-In track's mido.track object instance.
        USAGE:  Should only be called by _initilizeTracks(), and only then after the track has been
                created and populated with it's name and key signature.
        """
        ctTrack.append(mido.Message('control_change', channel=self.countTrackChannel, control=121, time=0)) #                   <-- Reset all controllers
        ctTrack.append(mido.Message('program_change', channel=self.countTrackChannel, program=countIn.instrument, time=0)) #    <-- 'Instrument' for Count
        ctTrack.append(mido.MetaMessage('midi_port', port=0, time=0)) #                                                         <-- Send MIDI data out of port 0


    def _calcSilence(self, song):
        """ Description: Determine midi clicks of silence and store in the outputMIDI data field.
        PARAM:  song - Instance of the Song class.
        USAGE:  This is a helper function for assemble_outputMIDI().
        Note:   The pre-roll silence is calculated as simply one full measure of silence * the
                number of measures specified in the CountIn.preRollDelay field.
        """
        silenceDuration = song.ticksPerBeat * song.timeSigNum
        silenceDuration *= song.countIn.preRollDelay
        self.songCurrPos = silenceDuration


    def _populateCountIn(self, song):
        """ Description: Populate CountIn track with count-in sequence as sped'd in song.countIn.countInModel
        Param:  song :Song class - Song object instance
        DOC: sd OutputMIDI._populateCountIn(Song)
        Note-1: Note that I am here assuming we have already made a call to countIn._buildCountModel() as
                part of the song spec display and user confirm of specs phase. I don't see why this
                would ever not be true, and I prefer to use the model as seen and confirmed by the user
                rather than risk regenerating it anew here.
        Note-2: The mido append 'note_on' message function does not permit a param for the note's channel
                number. When you append a new note_on message to a track mido automatically adds
                'channel=0' to the message, yet in multi-part songs generated from Musescore each
                instrument is assigned a unique channel number. As channel numbers define which synth
                for the given note's sound channel number params must be included in the note messages.
                I have seen that there is a 'private' function for the mido.Message object that
                allows you to set a specific parameter of a message instance, so I am using that
                to set the channel param for the added counting notes. When I do this the "Drumstick
                MIDI Player" for Linux and the "Midi Clef" player for Android gets the track names,
                channels, and instruments all correct, so this workaround does work.
        """
        #-----| Giving names to the countInModel 2D matrix columns
        measure = 0
        noteIdx = 1
        duration = 2
        #
        #-----| Declare local helper variables
        ctTrackIdx = song.trackInfo[-1][TI_OUTTRACKNUM] #   <-- mido track # of the count-in track I added
        ctChannel = self.countTrackChannel #                <-- channel # I've assigned from available, open, channels
        inPrePickup = False #                               <-- Used to sense when we are starting the pre-pickup measure countIn sequence
        offsetT0 = self.songCurrPos #                       <-- These are time offsets to use on next events per track-type.
        offsetTn = self.songCurrPos #                           (See doc_Notes.md for full details)
        offsetTct = self.songCurrPos #                          (Each initialized to the pre-roll silence duration)
        timeOffset = 0 #                                    <-- Used as helper to set final sync-point dummy notes
        #
        #-----| Add the count-in notes to the count-in output track
        for i, row in enumerate(song.countModel):
            if (row[measure] == 'P') and (inPrePickup is False):
                # Write a time-signature to begin the pre-pickup count sequence
                prePickupNum = song.timeSigNum - int(song.countIn.pickUpOnBeat)
                msg = mido.MetaMessage('time_signature', numerator=prePickupNum, denominator=song.timeSigDen, time=offsetT0)
                self.midiOut.tracks[0].append(msg)
                offsetT0 = 1 #                              <-- 1 MIDI click for next event just to be sure new time-sig is sensed by player
                offsetTn += 1
                offsetTct += 1
                self.songCurrPos += 1
                inPrePickup = True
            ctNote = song.countIn.notes[row[noteIdx]]
            msg = mido.Message('note_on', note=ctNote, velocity=song.countIn.velocity, time=offsetTct)
            msg._setattr('channel', ctChannel) #            <-- 'cheat' for setting correct channel #
            self.midiOut.tracks[ctTrackIdx].append(msg)
            msg = mido.Message('note_off', note=ctNote, velocity=0, time=row[duration])
            msg._setattr('channel', ctChannel)
            self.midiOut.tracks[ctTrackIdx].append(msg)
            offsetT0 += row[duration]
            offsetTn += row[duration]
            offsetTct = 0
            self.songCurrPos += row[duration]
        #
        #-----| Append the offset time-sync dummy text messages to each track.
        for i, row in enumerate(song.trackInfo):
            if row[TI_KEEP]:
                outTrackIdx = song.trackInfo[i][TI_OUTTRACKNUM]
                match outTrackIdx:
                    case 0:
                        timeOffset = offsetT0
                    case _ if outTrackIdx == ctTrackIdx:
                        timeOffset = offsetTct
                    case _:
                        timeOffset = offsetTn
                msg = mido.MetaMessage('text', text='BEGIN', time=timeOffset)
                self.midiOut.tracks[outTrackIdx].append(msg)
        self.songCurrPos += 1
        #
        #-----| Set Value for Each Track's Current Duration.
        for i, row in enumerate(song.trackInfo):
            row[TI_LENGTH] = self.songCurrPos


    def _populateOriginalSong(self, song):
        """ Description: Copies original song content into outputMIDI tracks, including multiple
            repeat copies if user has selected multiple repeats during specs confirm interaction.
        PARAM:  song - Instance of the Song class
        DOC:    See sd OutputMIDI._populateOriginalSong() in doc_UML.odg
        TODO:   Merge this method into _populateRepeatPlays() for a single method.
        """
        # for i, row in enumerate(song.trackInfo):
        #     if row[TI_KEEP] and (song.trackInfo[i][TI_OUTTRACKNUM] != song.trackInfo[-1][TI_OUTTRACKNUM]):
        #         print(f'=== | Copying Track-{i} to outputMIDI')
        #         self._copy_trackToOutput(song, i)
        #         print(f'TRACK-{i} COPIED | ===')
        # self._setCurrentDuration(song)
        # self._writeSyncPoint(song, 1)
        for r in range(1, song.playThroughs+1):
            for i, row in enumerate(song.trackInfo):
                if row[TI_KEEP] and (song.trackInfo[i][TI_OUTTRACKNUM] != song.trackInfo[-1][TI_OUTTRACKNUM]):
                    self._copy_trackToOutput(song, i)
                    display.progressMessage(f'Repeat-{r}, Track-{i} copied to output MIDI')
            self._setCurrentDuration(song)
            self._writeSyncPoint(song, r)


    def _copy_trackToOutput(self, song, trackIdx):
        """ Description: Copies song content from sourceMIDI over to outputMIDI for given trackIdx
        PARAM:  song - Instance of the Song class
        PARAM:  trackIdx - row# of the song.trackInfo 2D matrix - the track to copy from
        USAGE:  Before calling this function the song.outputMIDI._populateCountIn() must have been
                called in order to establish pre-conditions for this function to be successful.
        Note:   I have not here attempted to update song.songCurrPos as that would take some
                thought to do and I don't think I even need it.
        """
        DEBUG = False
        #DEBUG = True
        if DEBUG: print("In _copy_trackToOutput()")
        #
        #-----| Declare local helper variables
        outTrackNumber = song.trackInfo[trackIdx][TI_OUTTRACKNUM]
        inTrackNumber = trackIdx
        if DEBUG: print(f'outTrackNumber: {outTrackNumber}')
        #
        #-----| Copy the track's song content
        for msg in song.sourceMIDI.tracks[inTrackNumber]:
            if DEBUG: print(f'msg: {msg}')
            if msg.type != 'track_name' and msg.type != 'end_of_track':
                self.midiOut.tracks[outTrackNumber].append(msg)
                msgTime = msg.time
                song.trackInfo[trackIdx][TI_LENGTH] += msgTime
        if DEBUG: print(f"Track-{trackIdx} Length: {song.trackInfo[trackIdx][TI_LENGTH]}")
        if DEBUG: print("EXITING _copy_trackToOutput()")


    def _setCurrentDuration(self, song):
        """ Description: Determine song's current length in midi clicks and save to .songCurrPos
        PARAM: song - Instance of the Song class
        DOC:   See sd OutputMIDI._setCurrentDuration() in doc_UML.odg
        """
        self.songCurrPos = 0
        for i, row in enumerate(song.trackInfo):
            if row[TI_KEEP]:
                if row[TI_LENGTH] > self.songCurrPos: self.songCurrPos = row[TI_LENGTH]


    def _writeSyncPoint(self, song, repeatCount):
        """ Description: Write track sync-point message for alignment on repeat copies
        PARAM: song - Instance of the Song class
        DOC:   See sd OutputMIDI._writeSyncPoint() in doc_UML.odg
        """
        alignText = f"END-PLAYTHROUGH-{repeatCount}"
        for i, row in enumerate(song.trackInfo):
            if row[TI_KEEP] and (song.trackInfo[i][TI_OUTTRACKNUM] != song.trackInfo[-1][TI_OUTTRACKNUM]):
                offsetTime = self.songCurrPos - row[TI_LENGTH] + 1
                msg = mido.MetaMessage('text', text=alignText, time=offsetTime)
                self.midiOut.tracks[song.trackInfo[i][TI_OUTTRACKNUM]].append(msg)
                row[TI_LENGTH] += offsetTime


    def _closeTracks(self):
        """ Description: "Closes" out each track by appending an 'end_of_track' message to each.
        USAGE:  Should be called after work on each track has concluded, and before saving the .mid file.
        Note:   I don't think I any longer need this function.
        """
        #-----| Declare local helper variables
        for i, track in enumerate(self.midiOut.tracks):
            track.append(mido.MetaMessage('end_of_track', time=1))

    def writeFile(self):
        """ Description: Writes the completed MIDI file out to disk.
        """
        display.progressMessage("Writing output file")
        self.midiOut.save(self.outFilePath)

    def _find_openChannel(self, channelList):
        """ Description: Given list of in-use MIDI channels, find unused channel and store it
        PARAM:  channelList - unsorted list of in-use MIDI channels
        USAGE:  channelList is presumed to have been populated by Song class in populate_SongInfo()
        RESULT: An open channel for the new Count In track to use; or 99 if no open channel available
        NOTE:   Don't use the MIDI "percussion" channel, #10. Also cannot exceed 16 channels. Using
                base of 0, this means max channel # is 15.
        """
        openChan = 99 #                             <-- Presume invalid until we find an open channel
        lenChannelList = len(channelList)
        if lenChannelList < 16:
            channelList.sort()
            for i in range(0, lenChannelList):
                if i not in channelList:
                    if i != 9: #                    <-- Channel 9 (10) is special, don't use it'
                        openChan = i
            if openChan > 15: #                     <-- IF True, no 'holes' in channel list
                testChan = channelList[i] + 1 #     <-- So then get highest channel in use +1
                if testChan == 9: #                 <-- But make sure this then isn't channel #9 (10)
                    testChan += testChan
                openChan = testChan
        self.countTrackChannel = openChan
        if self.countTrackChannel == 99:
            errHandler.set_Error(4)


class CountIn:
    """ Description: Count-In specs, methods, and MIDI track to eventually add to Song.
    """

    def __init__(self):
        self.numFullMeasures = 1 #      <-- User can increase in the UI to have longer count-in
        self.pickUpOnBeat = 0.0 #       <-- If song has a pickup measure, on what beat is the first note?
        self.halfBeatCount = False #    <-- If True, we count 1 and 2 and 3 and ...
        self.track = mido.MidiTrack()
        self.trackDuration = 0 #        <-- After build_track() is called this will contain track total duration in MIDI ticks
        self.preRollDelay = 1 #         <-- Silence, in measures, to add to start of track
        self.instrument = 117 #         <-- Count using 'RotoTom' general MIDI instrument ID
        self.velocity = 80 #            <-- Volume to play the count-in notes
        self.notes = { #                <- A dictionary that defines count to MIDI note mapping
            1: 62,  # D4
            2: 64,  # E4
            3: 65,  # F4
            4: 67,  # G4
            5: 69,  # A4
            6: 71,  # B4
            7: 72,  # C5
            8: 74,  # D5
            "&": 60, # C4
            "rest": 127 #G8
        }
        self.countInModel = [] #        <-- A 2D matrix that will contain the count-in sequence
        self._ctNoteDuration = 0 #      <-- Counting note duration, based on halfBeatCount
        self._finalBeatPattern = 1 #    <-- Pickup measure case we have per doc_generate-countIn.md

    def populate_countModel(self, song):
        """ Description: Returns a 2D matrix that contains the count-in sequence.
        PARAM: song - Instance of the Song class
        RESULT: self.countInModel will be populated based on current song specs
        NOTE: See doc_generateCountIn.odg
        """
        self._buildCountModel(song)

    def build_Track(self, song):
        """ Description: Given song specs, create a MIDI track for the count-in
        Param: song :Song class - Data and methods of a Song object instance
        Result: self.track has been populated with the count-in MIDI data
        Returns: There is no return value
        TODO: Finalize approach to adding the preroll silence, including function encapsulation.
        """
        self._populate_trackMetaData(song)
            # Create 3 seconds of silence
        preRollSilenceTicks = self._calc_PreRollSilenceTicks(song)
        print(f'preRollDelayTicks: {preRollSilenceTicks}')
        self.track.append(mido.MetaMessage('set_tempo', tempo=song.tempoMIDI, time=preRollSilenceTicks)) # <-- Using this to position start of countIn after the silence
        self.trackDuration += preRollSilenceTicks
        self._populate_counts(song)

    # ----PRIVATE CLASS FUNCTIONS ------------------------------------------------------------------

    def _set_ctNoteDuration(self, ticksPerBeat):
        self._ctNoteDuration = ticksPerBeat
        if self.halfBeatCount:
            self._ctNoteDuration = int(self._ctNoteDuration / 2)

    def _set_finalBeatPattern(self):
        self._finalBeatPattern = 1
        if self.halfBeatCount and ((self.pickUpOnBeat - int(self.pickUpOnBeat)) == 0):
            self._finalBeatPattern = 2
        elif (not self.halfBeatCount) and ((self.pickUpOnBeat - int(self.pickUpOnBeat)) > 0):
            self._finalBeatPattern = 3
        elif self.halfBeatCount and ((self.pickUpOnBeat - int(self.pickUpOnBeat)) > 0):
            self._finalBeatPattern = 4

    def _buildCountModel(self, song):
        self.countInModel = [] # <-- Clear out any prior data from previous calls
        self._set_ctNoteDuration(song.ticksPerBeat)
        self._set_finalBeatPattern()
        for m in range(1, self.numFullMeasures+1):
            for b in range(1,song.timeSigNum+1):
                self._buildCountModel_addNext(m, b)
        for p in range(1, int(self.pickUpOnBeat)):
            self._buildCountModel_addNext('PU', p)
        self._buildCountModel_PUlastBeat()

    def _buildCountModel_PUlastBeat(self):
        DEBUG = False
        if DEBUG: print(f'_finalBeatPattern: {self._finalBeatPattern}')
        match self._finalBeatPattern:
            case 2:
                #turns out that, logically, for this case we don't need to do anything
                #about adding a 'final beat' to the pickup
                pass
            case 3:
                self.countInModel.append(['PU', int(self.pickUpOnBeat), int(self._ctNoteDuration/2)])
            case 4:
                self.countInModel.append(['PU', int(self.pickUpOnBeat), self._ctNoteDuration])
            case _:
                pass # <-- The default case is case #1, in which case we do nothing.

    def _buildCountModel_addNext(self, measure, beatNum):
        newRow = [measure, beatNum, self._ctNoteDuration]
        self.countInModel.append(newRow)
        if self.halfBeatCount:
            newRow = [measure, '&', self._ctNoteDuration]
            self.countInModel.append(newRow)

    def _populate_counts(self, song):
        """ Description: Populate CountIn track with the specified count-in sequence
        Param:  song :Song class - Data and methods of a Song object instance
        NOTE:   Note that I am here assuming we have already made a call to self._buildCountModel() as
                part of the song spec display and user confirm of specs phase. I don't see why this
                would ever not be true, and I prefer to use the model as seen and confirmed by the user
                rather than risk regenerating it anew here.
        TODO
        """
            # Giving names to the countModel 2D matrix rows
        # measure = 0 # <-- We don't use this here
        noteIdx = 1
        duration = 2
        for row in song.countModel:
            ctNote = self.notes[row[noteIdx]]
            ctDuration = row[duration]
            msg = mido.Message('note_on', note=ctNote, velocity=64, time=0)
            self.track.append(msg)
            msg = mido.Message('note_off', note=ctNote, velocity=0, time=ctDuration)
            self.track.append(msg)

    def _populate_trackMetaData(self, song):
        """ Description: Populate metadata about the song at start of CountIn track (tempo, key, etc)
        Param: song :Song class - Data and methods of a Song object instance
        USAGE: This function begins the CountIn track population process, so we will start by clearing the track
        NOTE
        TODO
        """
        self.track.clear()
        self.trackDuration = 0
        msg = mido.MetaMessage('track_name', name='Count In')
        self.track.append(msg)
        msg = mido.MetaMessage('key_signature', key='C')
        self.track.append(msg)
        msg = mido.MetaMessage('time_signature', numerator=song.timeSigNum, denominator=song.timeSigDen)
        self.track.append(msg)
        msg = mido.MetaMessage('set_tempo', tempo=song.tempoMIDI)
        self.track.append(msg)
        msg = mido.Message('control_change', channel=0, control=121) # <- Reset all controllers to their default. Not fully sure what this does, but I see it at the start of MuseScore midi exported files.
        self.track.append(msg)
        msg = mido.Message('program_change', channel=0, program=self.instrument, time=0) #< -- Set the 'patch', or instrument, the synth should play from the soundfount file.
        self.track.append(msg)


class Song:
    """ Description: Represents and characterizes the song we are operating on.
    Method: populate_SongInfo(self, sourceMIDI :mido.MidiFile)
    NOTE-2: This class 'is composed of ' the classes: CountIn, OutputMIDI and a mido.MidiFile class
            that contains the input MIDI file.
    NOTE-1: I am using getter/setter, or in Python terms @property, functions in a good-faith
            attempt to minimize consistency errors by having co-dependent attributes stay in sync via
            those @ property functions. But this was sloppily done. I have not really engineered out
            which properties really ought to be 'private' v 'public', nor have I worked out all the
            likely co-dependencies and potential interactions effects. So bugs or anomalies may
            appear given the way I have it now.
    """

    def __init__(self, inputFile, outputFile):
        """ Description: Initilizes class data.
        PARAM: inputFile - validated path to the input MIDI file
        PARAM: outputFile - validated path we will write the output MIDI file to
        """

        #-----| GLOBAL VARIABLES TO REFERENCE COLUMNS IN trackInfo 2D MATRIX ----------------------
        global TI_NAME, TI_CHANNEL, TI_KEY, TI_INSTRUMENT, TI_KEEP, TI_FIRSTNOTE, TI_SONGOFFSET, TI_LENGTH, TI_OUTTRACKNUM
        TI_NAME = 0 #           <-- track name, as potentially edited by user
        TI_CHANNEL = 1 #        <-- Track's channel # (but, could be more than one channel)
        TI_KEY = 2 #            <-- track's key signature
        TI_INSTRUMENT = 3 #     <-- MIDI instrument # (but is really channel dependent)
        TI_KEEP = 4 #           <-- keep or discard source track
        TI_FIRSTNOTE = 5 #      <-- Index to source tracks first 'note_on' message
        TI_SONGOFFSET = 6 #     <-- Track's 1st note_on time offset from 0
        TI_LENGTH = 7 #         <-- Track's length in midi clicks
        TI_OUTTRACKNUM = 8 #    <-- Track # in the outputMIDI file

        #-----| CLASS INTERNAL DATA STRUCTURE -----------------------------------------------------
        self.countIn = CountIn()
        self.sourceMIDI = mido.MidiFile(inputFile)
        self.outputMIDI = OutputMIDI(outputFile)
        self.ticksPerBeat = 0 #             <- Must be set before .songLengthTicks.
        self.timeSigNum = 0
        self.timeSigDen = 0
        self.firstTimeSig = mido.Message #  <- Needed for pickup measures. See doc_AssembleOutputMIDI.md
        self.songLengthBPM = 0
        self.songLengthSeconds = 0
        self._songLengthTicks = 0
        self.key = ""
        self.tempoMIDI = 0
        self._tempoBPM = 0
        self.playThroughs = 1 #         <-- Number of times we'll replicate original tracks for add'l loops
        self.numTracks = 0 #            <-- Not including the countIn track
        self.trackInfo = list() #       <-- A 2D matrix of track-specific info, where 'x' is the index to the sourceMIDI track:
        #                                   [x, 0]: Source Track Name
        #                                   [x, 1]: Track Base MIDI Channel
        #                                   [x, 2]: Track Initial Key Signature
        #                                   [x, 3]: Track Initial MIDI Instrument Number
        #                                   [x, 4]: True = Include track in outputMIDI
        #                                   [x, 5]: Index to Original Track's 1st Note-On Message
        #                                   [x, 6]: Track's 1st note_on time offset from 0
        #                                   [x, 7]: Track's length in midi clicks
        #                                   [x, 8]: Index to outputMIDI Track #
        #                               This matrix initially populated in Song.populate_SongInfo()


    @property
    def tempoBPM(self):
        return self._tempoBPM

    @tempoBPM.setter
    def tempoBPM(self, bpm):
        self._tempoBPM = bpm
        #
        # ---- Need to handle case where we are setting .tempoMIDI, but we don't yet have
        #      the time signature. This will actually be the case when we first call this.
        #      If on that 1st call we set tempoMIDI to 0 then we always will show user the
        #      default value for tempo in the UI.
        #      NOTE: probably because of some redesign along the way I have made this too
        #            complicated and messy. Could be ripe for cleanup.
        if self.timeSigNum==0 or self.timeSigDen==0:
            pass
        else:
            self.tempoMIDI = mido.bpm2tempo(bpm, time_signature=(self.timeSigNum,self.timeSigDen))
        if self.ticksPerBeat <= 0:
            self.songLengthSeconds = 0
        else:
            lenInQtrNotes = self.songLengthTicks / self.ticksPerBeat
            self.songLengthSeconds = round((lenInQtrNotes * self.tempoMIDI) / 1000000)


    @property
    def songLengthTicks(self):
        return self._songLengthTicks

    @songLengthTicks.setter
    def songLengthTicks(self, ticks):
        self._songLengthTicks = ticks
        if self.ticksPerBeat <= 0:
            self.songLengthSeconds = 0
        else:
            lenInQtrNotes = self._songLengthTicks / self.ticksPerBeat
            self.songLengthSeconds = round((lenInQtrNotes * self.tempoMIDI) / 1000000)

    @property
    def countModel(self):
        # TODO: Break this out into a getter/setter so that I am not regenerating the model
        #       each time I go to simply read/use it.
        self.countIn.populate_countModel(self)
        return self.countIn.countInModel


    def populate_SongInfo(self):
        """ Description: Populate song with input MIDI file specs and characteristics
        Usage: A Song class instance is created in the main body of the code; sometime
               later, after the source MIDI file has been opened and verified, this
               method is called to inspect the source MIDI file and populate this
               class-instance with the necessary song specs. (This approach reduces
               timing dependent coupling between Song and the process to open/verify
               the input file.)
        Note:  In the case statements below I am always testing to see if I have already
               captured the message/parameter of interest. If so, then I ignore the match.
               I am doing this because I don't want to inadvertenly pickup changes that may
               be in the track later in the song, I only want the initial values. So, e.g., if
               there is, say, a tempo or program instrument change halfway through the song I don't
               want that as the starting tempo or instrument.
        Note:  What I'm doing with the gotInitialTimeSig variable and self.firstTimeSig may seem
               confusing. I am trying to get the last time signature before the first audible
               note. Which will be the time signature that needs to be in effect at the start of
               the original song. I need to use this when copying the original track-0 over to the
               OutputMIDI. See: doc_NotesOnTimeSignature.md
        TODO:  Call this function from _init_() vs keeping it a seperate step in the main body.
        """
        #
        #-----| Declare Local Helper Variables ----------------------------------------------------
        gotInitialTimeSig = False # <-- Used to help us get last time-sig before 1st 'note_on' in track-0
        gotFirstNoteOn = False #    <-- Used flag that we reached 1st 'note_on' message in a track
        trackRunTime = 0 #          <-- To accumulate each track's length in midi clicks
        channelList = [] #          <-- Used to find first available MIDI channel to use for count track.
        #
        #-----| Collect Some Initial Song 'Global' Data Readily Available from mido ---------------
        song.songLengthSeconds = int(self.sourceMIDI.length)
        song.ticksPerBeat = self.sourceMIDI.ticks_per_beat
        #
        #-----| Interrogate All Messages in All Tracks to Collect Needed Song Data-----------------
        for i, track in enumerate(self.sourceMIDI.tracks):
            self.numTracks += 1
            gotFirstNoteOn = False
            trackRunTime = 0
            self.trackInfo.append([track.name, -1, 'X', -1, True, -1, -1, -1, -1]) # <-- Initilize row in the 2D matrix
            for msg in track:
                match msg.type:
                    case 'time_signature':
                        if self.timeSigDen == 0:
                            self.timeSigNum = msg.numerator
                            self.timeSigDen = msg.denominator
                        if gotInitialTimeSig is False:
                            self.firstTimeSig = msg
                    case 'set_tempo':
                        if self.tempoMIDI == 0:
                            self.tempoMIDI = msg.tempo
                            self.tempoBPM = round(mido.tempo2bpm(self.tempoMIDI))
                    case 'key_signature':
                        if self.key == "":
                            self.key = msg.key
                        if self.trackInfo[i][TI_KEY] == "X":
                            self.trackInfo[i][TI_KEY] = msg.key
                    case 'program_change':
                        channelList.append(msg.channel)             # See doc_NotesOnChannelNumber.md
                        if self.trackInfo[i][TI_INSTRUMENT] == -1:  # See doc_NotesOnProgramChanges.md
                            self.trackInfo[i][TI_INSTRUMENT] = msg.program
                            self.trackInfo[i][TI_CHANNEL] = msg.channel
                    case 'note_on':
                        if self.trackInfo[i][TI_CHANNEL] == -1:     # See doc_NotesOnChannelNumber.md
                            self.trackInfo[i][TI_CHANNEL] = msg.channel
                        gotInitialTimeSig = True                    # When I hit the first note_on, assume I got best time-sig guess
                        if gotFirstNoteOn is False:
                            song.trackInfo[i][TI_FIRSTNOTE] = i
                            song.trackInfo[i][TI_SONGOFFSET] = trackRunTime + msg.time
                            gotFirstNoteOn = True
                    case _:
                        pass
                trackRunTime += msg.time
            song.trackInfo[i][TI_LENGTH] = trackRunTime
        #
        #-----| populate defaults for any missing params ------------------------------------------
        if self.tempoMIDI == 0:
            self.tempoMIDI = 500000                                 # 120 BPM
            self.tempoBPM = round(mido.tempo2bpm(self.tempoMIDI))
        if self.timeSigDen == 0:                                    # Default to 4/4 time.
            self.timeSigNum = 4                                     # BUT should never happen, if
            self.timeSigDen = 4                                     # it does, user should prob be
        if gotInitialTimeSig is False:                              # shown a warning?
            self.firstTimeSig = mido.MetaMessage('time_signature', numerator=self.timeSigNum, denominator=self.timeSigDen)
        #
        #-----| Determine Some Additional Params From Above Collected Data ------------------------
        self.songLengthTicks = self._getMaxInColumn(song.trackInfo, TI_LENGTH)
        self.songLengthBPM = round(self.songLengthTicks/self.sourceMIDI.ticks_per_beat)
        self.outputMIDI._find_openChannel(channelList)
        self.trackInfo.append(['Count In', self.outputMIDI.countTrackChannel, 'C', self.countIn.instrument, True, -1, -1, -1, -1])
        self._flagMutedTracks()


    def __repr__(self):
        dispString = 'Class Song - Current Attributes\n'
        dispString += '============================================================================\n'
        dispString += f' \
        Source File for Song: {self.sourceMIDI.filename}\n \
        Key Signature: {self.key}\n \
        Time Signature: {self.timeSigNum}/{self.timeSigDen}\n \
        Tempo (BPM): {self.tempoBPM}\n \
        Tempo (MIDI): {self.tempoMIDI}\n \
        Beat Pickup Starts On: {self.countIn.pickUpOnBeat}\n \
        Song Length Before Count-In (Beats): {self.songLengthBPM}\n \
        Song Length Before Count-In (Seconds): {self.songLengthSeconds}\n \
        Song Length Before Count-In (Ticks): {self.songLengthTicks}\n \
        Ticks Per Beat: {self.ticksPerBeat}\n'
        for i, trackName in enumerate(self.trackName):
            dispString += 'Track-{}: {}\n'.format(i, trackName)
        return dispString


    def set_SongLength_Seconds(self):
        """ The song length in seconds needs to be recalculated each time the tempo changes.
            The calculation is based on the MIDI microseconds per quarter note and the number
            of quarter-note beats in the song.
        """
        if self.ticksPerBeat <= 0:
            self.songLengthSeconds = 0
        else:
            lenInQtrNotes = self.songLengthTicks / self.ticksPerBeat
            self.songLengthSeconds = round((lenInQtrNotes * self.tempoMIDI) / 1000000)


    def build_outputMidi(self):
        """ Description: When called it uses the song specs to build the outputMIDI tracks.
        USAGE:  Called from main body to access the embedded OutputMIDI class. Should only
                be called once the song specs have been validated/edited by the user.
        """
        self.outputMIDI.assemble_outputMIDI(self)


    def write_outputFile(self):
        """ Description: When called it writes the output MIDI file, with the count-in now added.
        USAGE:  Called from main body to access the embedded outputMIDI class function. Should only
                be called after all track-processing has been completed. I.e., build_outputMidi() has
                been sucessfully executed.
        """
        self.outputMIDI.writeFile()


    def _find_openChannel_DEPRECATE(self, channelList):
        """ Description: Given a list of in-use MIDI channels, returns an unused channel
        PARAM:   channelList - unsorted list of in-use MIDI channels
        USAGE:   channelList is presumed to have been populated by song class in populate_SongInfo()
        RETURNS: An open channel for the new Count In track to use; or 99 if no open channel available
        NOTE:    Don't use the MIDI "percussion" channel, #10. Also cannot exceed 16 channels. Using
                 base of 0, this means max channel # is 15.
        """
        openChan = 99 #                             <-- Presume invalid until we find an open channel
        lenChannelList = len(channelList)
        if lenChannelList < 16:
            channelList.sort()
            for i in range(0, lenChannelList):
                if i not in channelList:
                    if i != 10: #                   <-- Channel 10 is special, don't use it'
                        openChan = i
            if openChan > 15: #                     <-- IF True, no 'holes' in channel list
                testChan = channelList[i] + 1 #     <-- So then get highest channel in use +1
                if testChan == 10: #                <-- But make sure this then isn't channel #10
                    testChan += testChan
                openChan = testChan
        return openChan

    def _getMaxInColumn(self, inList, colNumber):
        """ Description: Given a 2D list and column number, find the max value in that column
        PARAM:  inList - a 2-dimensional list-matrix
        PARAM:  colNumber - an integer that tells the function what column to use
        USAGE:  We are presuming the columnn of interest contains integers
        Result: Returns the maximum value in colNumber
        """
        highVal = max(row[colNumber] for row in inList)
        return highVal


    def _flagMutedTracks(self):
        """ Description: Mark what appear to be muted tracks as 'Remove' instead of 'Keep'
        Usage:  Should only be called at the end of song.populate_SongInfo(). In any event, that
                function must be called prior to calling this function.
        """
        for i in range(1, len(self.trackInfo)-1): # <-- Do not include track-0 or the count-in track in this assessment
            if self.trackInfo[i][TI_FIRSTNOTE] == -1:
                self.trackInfo[i][TI_KEEP] = False


# =================================================================================================
#    CLASS DEFINITIONS - USER INTERFACE (or maybe the 'VIEW' in MVC model)
# =================================================================================================

class Terminal:
    """ This class abstracts the command line terminal.
        It contains terminal related global variables and constants that are used by all other
        terminal display and user-interaction classes.
    """

    def __init__(self):
        self.cls = '\033[2J\033[H' #    <-- Clear screen
        self.hlON = '\033[93;1m' #      <-- Bright yellow highlight terminal text
        self.hlGreenON = '\033[92;1m' # <-- Bright green terminal text
        self.hlERROR = '\033[91;1m' #   <-- Bright red highlight terminal text
        self.hlOFF = '\033[0m' #        <-- Normal terminal text
        self.headerColWidth = 100
        self.indentColWidth = 8
        self.lableColWidth = 50

    def clearScreen(self):
        print("\033[2J\033[H", end="")


class TerminalDisplay(Terminal):
    """ Description: Provides displays and views onto terminal screen
    METHOD:
    METHOD:
    USAGE:  Intention is that you pass to each method it's needed input data, then the method
            uses that data to build and "print" onto the terminal the requested display or
            view.
    NOTE:
    TODO:
    """

    def __init__(self):
        """ NOTE:   I think I've recently learned that in Python static, i.e. constant, properties
                    ought to be defined at the Class level and not in an _init_ function.
                    That way they would be constants for any instance of the class.
        """
        super().__init__()

    def songHeader(self, fillChar="="):
        """ Description: Displays a header suitable for display at the top of the song parameter list.
        """
        preamble = f"{''.ljust(4, fillChar)} midi-countin.py, ver: {__version__} "
        fillLength = self.headerColWidth - len(preamble)
        print(f"{preamble}{''.ljust(fillLength, fillChar)}")
        print('')


    def countIn_string(self, song):
        """ Description: Display a rendering of the count-in sequence
        PARAM: song - instance of the Song class
        RESULT: Displays a string on the terminal showing what the rendered count sequence will be
        NOTE: See doc_CountInRules.md and doc_generateCountIn.odg for the logic of how this works
        """
        ctDisp = ""
        currentMeasure = 0
        measure = 0 # <-- Giving names to the countModel 2D matrix rows
        noteIdx = 1
        #duration = 2 <-- Not used here
        for row in song.countModel:
            if row[measure] != currentMeasure:
                ctDisp += " |"
                currentMeasure = row[measure]
            ctDisp += f' {row[noteIdx]}'
        if currentMeasure != 'PU': ctDisp += " |"
        print(f'COUNT-IN SEQUENCE: {self.hlGreenON}{ctDisp}{self.hlOFF}', end="")
        print(f' --> on MIDI channel # {song.outputMIDI.countTrackChannel}')


    def songInfo(self, song, blankLines=1, forConfirm=False):
        """ Description: Show user count-in and song specs for them to review and edit as needed
        Param:  song :Song instance - provides specs for input MIDI song to confirm or edit
        Param:  blankLines :int - Number of blank lines to add above the output display
        Param:  forConfirm :bool - If True, output contains user editing instructions.
        Usage:  Primary intent is to call this as an internal helper function during user
                review and edit of song info. But can also be called 'at will' to display all the
                specs a a view without editing enabled.
        Note-1: This implementation is a 'brute-strength' implementation, no finesse here.
        Note-2: The below songDisplaySet list structures what, and how, we're going to display from the
                song view of parameters. The last boolean value in each tuple defines if that
                parameter is editable by the user when the passed-in forConfirm flag is True.
        """
        songDisplaySet = self._build_songDisplaySet(song)
        self.countIn_string(song)
        for i in range(0, blankLines):
            print('')
        self.sepLine(0,0,'-')
        self._show_displaySet(song, songDisplaySet, forConfirm)


    def trackList(self, song, forConfirm=False, trackToEdit=-1):
        """ Description: Display onto terminal the list of all tracks present in input MIDI file.
        Param:  song :Song instance - provides specs for input MIDI song to confirm or edit
        Param:  forConfirm :bool - If True, output contains user editing instructions.
        Param:  trackToEdit :int - If >0 that specific track will be displayed in a format
                appropriate for the user to make edits to select parameters.
        Doc:    sd TerminalDisplay.trackList() in doc_UML.odg
        """
        for i, row, in enumerate(song.trackInfo):
            if i == trackToEdit:
                self.track_toEdit(song, i)
            else:
                self.track_forDisplay(song, i, forConfirm)


    def track_forDisplay(self, song, trackIndex, forConfirm):
        """ Description: Display a specific track's info onto terminal.
        Param:  song :Song instance - provides specs for input MIDI song to confirm or edit
        Param:  trackIndex :int - the track#, in song.trackInfo[][] to show
        Param:  forConfirm :bool - If True, output is formatted to support user selection for editing
                Note, however, that regardless of value of forConfirm, the count-in track will not
                display as being editable.
        Doc:    sd TerminalDisplay.track_forDisplay() in doc_UML.odg
        """
        #
        #----- Initialize Helper Variables
        displayString = ""
        displayChannelNum = song.trackInfo[trackIndex][TI_CHANNEL]
        notCountTrack = False #    <-- Used to supress editable display of the count-in track
        #
        #----- Set helper values for determining proper display output
        editIndex = f"T{trackIndex}"
        if song.trackInfo[trackIndex][TI_CHANNEL] < 0: displayChannelNum = 'x'
        trackLable = f"Track-{trackIndex} (ch-{displayChannelNum} key-{song.trackInfo[trackIndex][TI_KEY]}): {song.trackInfo[trackIndex][TI_NAME]}"
        trackRetain = "Keep"
        if song.trackInfo[trackIndex][TI_KEEP] != True: trackRetain = "Remove"
        if trackIndex != (len(song.trackInfo) - 1): notCountTrack = True
        #
        #----- Pick appropriate formatting function call
        if forConfirm and notCountTrack:
            displayString = self._buildParamDisplayString_forEdit(trackLable, trackRetain, editIndex)
        else:
            displayString = self._buildParamDisplayString_noEdit(trackLable, trackRetain)
        #
        #----- Output track-line to the terminal
        print(displayString)


    def track_toEdit(self, song, trackIndex):
        """ Description: Display a specific track in a form suitable for user to edit it's parameters
        Param:  song :Song instance - provides specs for input MIDI song to confirm or edit
        Param:  trackIndex :int - the track#, in song.trackInfo[][] to show
        Doc:    sd TerminalDisplay.track_forEdit() in doc_UML.odg
        """
        trackDisplaySet = self._build_trackDisplaySet(song, trackIndex)
        display.sepLine()
        display._editHeader(retry=False)
        print(f"Track-{trackIndex}:")
        self._show_displaySet(song, trackDisplaySet, True)
        display.sepLine()


    def track_namesForFile(self, midiFile: mido.MidiFile, fileDescript=""):
        """ Description: Displays all track names from midiFile.
        PARAM:  midiFile - a mido.MidiFile instance (not a specific track)
        PARAM:  fileDescript - Text for a short, human readable, file description.
        Note:   Track names are in metamessages. Depending on how the midi file was created,
                there may not be a name for each track.
        """
        print(f'Tracks in {fileDescript}:')
        for i, row, in enumerate(midiFile.tracks):
            print(f"   Track-{i}: {row.name}")

    def track_messagesForFile(self, midiFile: mido.MidiFile, fileDescript=""):
        """ Description: Displays all messages in all tracks for given midiFile.
        PARAM:  midiFile - a mido.MidiFile instance (not a specific track)
        PARAM:  fileDescript - Text for a short, human readable, file description.
        """
        print("")
        print('-' * 80)
        print(f'Number of Tracks in {fileDescript}: {len(midiFile.tracks)}')
        print('-' * 80)
        for i, track, in enumerate(midiFile.tracks):
            print(f'\n=== All-Messages for Track {i} | {midiFile.tracks[i].name}')
            self.track_messagesAll(track)
            print("")
            print("")

    def track_messagesAll(self, midoTrack):
        """ Description: Displays all the messages in the mido.track object
        PARAM: midoTrack - param of type mido.track, a class from the mido library.
        RESULT: Displays a list of the MIDI messages onto stdout.
        RETURNS: Length of track in midi ticks.
        USAGE:  By design this is a bare-bones display. Just lists the messages
                onto the screen. It is up to the calling code/function to wrap
                any header/footer display around this listing.
        """
        runningTime = 0
        for msg in midoTrack:
            print(f"{runningTime:06} {msg}")
            runningTime += msg.time
        return runningTime
        print('')

    def track_MessagesMeta(self, midoTrack):
        """ Description: Displays all the META-messages in a mido.track object
        PARAM: midoTrack - param of type mido.track, a class from the mido library.
        RESULT: Displays a list of meta messages onto stdout.
        RETURNS: Length of track in midi ticks.
        USAGE:  By design this is a bare-bones display. Just lists the messages
                onto the screen. It is up to the calling code/function to wrap
                any header/footer display around this listing.
        """
        print(f'\n=== Meta-Messages for Track | {midoTrack.name}')
        runningTime = 0
        for msg in midoTrack:
            if msg.is_meta:
                print(f'{runningTime:06} {msg}')
            runningTime += msg.time
        return runningTime


    def progressMessage(self, msgText):
        """ Description: Displays text to terminal.
        Usage: To inform user of progress. msgText should be just a brief single line of text.
        """
        print(f'===> {msgText}')


    def sepLine(self, blankBefore=0, blankAfter=0, fillChar="="):
        """ Description: Displays a group or section separator line.
        """
        for i in range(0, blankBefore):
            print('')
        print(f"{''.ljust(self.headerColWidth, fillChar)}")
        for i in range(0, blankAfter):
            print('')


    def _build_songDisplaySet(self, song):
        """ Description: Creates a 2D list of song parameters suitable for display onto the terminal.
        Param:  song :Song instance - provides specs for input MIDI song to confirm or edit
        USAGE:  Was created for use during the user verification & edit of song parameters.
        """
        songDisplaySet = [
            ("Source Filepath", song.sourceMIDI.filename, False),                  # <-- I think I want to show the whole pathname.
            #("Source File", os.path.basename(song.sourceMIDI.filename), False),   # <- display base filename, without path
            ("# Measures of Count-In", song.countIn.numFullMeasures, True),
            ("Beat Pickup Starts On", song.countIn.pickUpOnBeat, True),
            ("Count on Half-Beats?", song.countIn.halfBeatCount, True),
            ("Key Signature", song.key, True),
            ("Time Signature", f"{song.timeSigNum}/{song.timeSigDen}", True),
            ("Song Play-Throughs", f"{song.playThroughs}", True),
            ("Tempo (BPM)", song.tempoBPM, False),
            ("Tempo (MIDI micros)", song.tempoMIDI, False),
            ("Song Length Before Count-In (Beats)", song.songLengthBPM, False),
            ("Song Length Before Count-In (Seconds)", song.songLengthSeconds, False),
            ("Song Length Before Count-In (Ticks)", song.songLengthTicks, False),
            ("Ticks Per Beat", song.ticksPerBeat, False)]
        return songDisplaySet


    def _build_trackDisplaySet(self, song, trackIdx):
        """ Description: Creates a 2D list of track parameters suitable for display onto the terminal.
        Param:  song :Song instance - provides specs for input MIDI song to confirm or edit
        Param:  trackIdx :int - track number we are building display set for
        USAGE:  Was created for use during the user verification & edit of a specific track's parameters.
        """
        keepTxt = "Remove"
        keepEditable = True
        if song.trackInfo[trackIdx][TI_KEEP]: keepTxt = "Keep" #    <-- Convert bool info to user-friendly display text
        if trackIdx == 0: keepEditable = False #                    <-- Do not display Track-0 as being removable
        trackDisplaySet = [
            ("Track Name", song.trackInfo[trackIdx][TI_NAME], True),
            ("Key Signature", song.trackInfo[trackIdx][TI_KEY], True),
            ("Keep?", keepTxt, keepEditable)]
        return trackDisplaySet


    def _show_displaySet(self, song, displaySet, forConfirm=False):
        editIndex = 0
        for lable, value, edit in displaySet:
            if edit and forConfirm:
                editIndex += 1
                print(self._buildParamDisplayString_forEdit(lable, value, editIndex))
            else:
                print(self._buildParamDisplayString_noEdit(lable, value))


    def _buildParamDisplayString_noEdit(self, label, value):
        """ Private helper function that formats a non-editable song parameter for display.
        """
        displayString = f"{''.rjust(self.indentColWidth,' ')}{label.ljust(self.lableColWidth, '.')}{value}"
        return displayString

    def _buildParamDisplayString_forEdit(self, label, value, editIndex):
        """ Private helper function that formats an editable song parameter for display.
        """
        tempStr = f"[{editIndex}] "
        displayString = f"{self.hlON}{tempStr.rjust(self.indentColWidth, ' ')}{self.hlOFF}{label.ljust(self.lableColWidth, '.')}{self.hlON}{value}{self.hlOFF}"
        return displayString

    def _editHeader(self, retry=False):
        """ Description: Displays a header suitable for the user-editing of song params activity
        """
        print('Count-In Track will be added based on the following Characteristics.')
        print('ENTER C to continue, Q to quit and exit, or the number of a parameter to modify:')
        print(f"{''.ljust(self.headerColWidth, '=')}")




class UserInterface(Terminal):
    """ As this is a CLI program, this class in effect, represents stdout/stdin.
        TODO: Separate out the 'display' methods into a controller class. And in
              those methods try to mostly call into View display classes. E.g.,
              like the Track_View class. Result being that this class is really
              a container for a set of functions that the main body of code
              will rely on to drive display activities based on various
              pathways through the code (e.g., if command line is 'info-only').

        TODO: I think we should have a top-level class that represents a 'frame'
              of sorts on the terminal which is the space of the user I/O. And
              so then the top-level class that would represent that space would
              define columns, highlight text colors, etc. And maybe ideally
              even build out the capability to keep track of what line we are on
              so that user see's a static 'space' as we go back up lines as
              needed during the edit-redisplay cycle. But now have this
              top-level class be very light, with functions to control the
              terminal. Other UI classes would be used to format the data and
              spit it out onto the terminal. This needs some thought.
        ASSUMES:
            - The 'song' class is passed in by reference. That class represents,
              and contains, the data that characterizes the song, such as time
              signature, tempo, etc.
    """

    def __init__(self):
        """ TODO: These properties are all static 'constants.' I think I've recently learned
            that in Python these ought to be defined at the Class level and not in
            an _init_ function. That way they would be constants for any instance of
            the class. Tho in this case there really is only one instance, so as a
            practical matter, it doesn't really matter.
        """
        super().__init__()
        # self.args <- is set in input_commandline

    def input_commandline(self):
        """ Description: Configures, and ingests, the command line as typed in the terminal by the user
        USAGE:   Call in main body of the code to fetch the command line string and parse it out into
                 the individual parameter-value pairs.
        RESULT:  self.args will contain the parsed out command line arguments.
        RETURNS: True if both input and output file params contain valid paths to each respective file.
        NOTE:    - Hyphens in command line param names get converted to an underscore for variable
                 name reference purposes.
                 - To access a param defined with type=argparse.FileType('r') you need to go an add'l
                 level deeper into the object. E.g., args.file_path.name.
        REF: https://machinelearningmastery.com/command-line-arguments-for-your-python-script/
        """
        helpDescript = sys.argv[0].split("/")[-1] + ",  Version: " + __version__ + " || " + __doc__
        parser = argparse.ArgumentParser(description=helpDescript, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument("-io", "--info_only", action="store_true", help="Show song info but take no action.")
        parser.add_argument("-v", "--verbose", action="store_true", help="Show all info and activity on terminal screen.")
        parser.add_argument("-i", "--input-file-path", help="Input MIDI file to add count to. May be full path to file.")
        parser.add_argument("-o", "--output-file-path", default="TEST_Output.mid", help="Output file name, may be full path to file. Default is input file with OUT added to the end.")
        args = parser.parse_args()
        if args.verbose:
            print(f'\nCommand Line Arguments: {args}')
        self.args = args
        return self._files_Valid()

    def interact_ConfirmSpecs(self, display, song):
        """ Description: Terminal UI for user to review and edit song and count specs; then proceed or quit
        Param:  self :Virtual param to class instance data & methods
        Param:  ctIn :CountIn instance - provides specs for the count-in to confirm or edit
        Param:  song :Song instance - provides specs for input MIDI song to confirm or edit
        Usage:  Called from the main body of code for the user to inspect song and count-in specs, and
                edit as necessary. Will then offer to user options to Quit or Continue on to make the
                count-in track and produce the output MIDI file.
        Note:   This implementation is a 'brute-strength' implementation, no finesse here.
        Doc:    See diagram sd UserInterface.interact_ConfirmSpecs in doc_UML.odg
        TODO:   Implement editing for Tracks.
        """
        #
        #----- Initialize Helper Variables
        specsOK = False #   <-- When it goes True we exit the function
        retry = False #     <-- Used to show a 'input is invalid, try again' message to user in _getUserEditChoice() when True
        group = 'X' #       <-- Flags if user wants to edit a song param ('P') or a track ('T')
        numberVal = -1 #    <-- The number portion of user input (e.g., song param# or track# to edit)
        #
        #----- Loop Until User Confirms Specs or Requests to Quit
        while specsOK == False:
            display.clearScreen()
            display.songHeader()
            display._editHeader()
            display.songInfo(song, blankLines=0, forConfirm=True)
            display.sepLine(0,0,'-')
            display.trackList(song, True, -1)
            retry, group, numberVal = self._getUserEditChoice(retry)
            match group:
                case 'P':
                    retry = not self._interact_EditParam(song, numberVal) #   <-- Returns False if there is invalid user input
                case 'T':
                    retry = not self._interact_EditTrack(song, numberVal)
                case "C":
                    retry = False
                    specsOK = True
                case _:
                    retry = True
                    specsOK = False
        return True

    def _getUserEditChoice(self, retry=False):
        display.sepLine(0,0,'-')
        if retry:
            print(self.hlERROR, end="")
            print('*** Unrecognized Input - Please try again ***')
            print(self.hlOFF, end="")
        print(self.hlON, end="")
        userInput = input('C, Q or Line# to Edit: ')
        print(self.hlOFF, end="")
        if userInput.isdigit(): #                               <-- User entered a number; so edit a specific parameter
            val = int(userInput)
            group = 'P'
            valid = True
        else:
            match userInput.lower():
                case str() as s if s.startswith('t') and s[1:].isdigit():
                    group = 'T'
                    val = int(s[1:])
                    valid = True
                case "q":
                    group = 'X'
                    val = -1
                    valid = True
                    print("Exited at User Request.")
                    sys.exit(0)
                case "c":
                    group = 'C'
                    val = -1
                    valid = True
                case _:
                    group = 'X'
                    val = -1
                    valid = False
        return valid, group, val


    def _interact_EditParam(self, song, paramIndex):
        """ Description: Handle user interaction for song parameter editing.
        Param:  song - Instance of the Song class.
        Param:  paramIndex - the index number of the editable song spec param as seen by the user.
        Note:   The paramIndex is tied to the case statements directly. Not elegant in that any
                changes to the songDisplaySet[] in TerminalDisplay.songInfo() will have to be
                accounted for here as well.
        TODO:   Tweak to match the userInput validation form of _interact_EditTracl(self, userInput, song)
        """
        editValid = False
        print(self.hlON, end="")
        match paramIndex:
            case 1:
                userInput = input('ENTER Number of Full Measures to Count: ')
                if userInput.isdigit():
                    song.countIn.numFullMeasures = int(userInput)
                    editValid = True
                else:
                    editValid = False
            case 2:
                userInput = input('ENTER Beat First Pickup Note Starts On: ')
                try:
                    userInputFloat = float(userInput)
                    if userInputFloat * 10 % 5 == 0: # <-- Allowing increments of .5 only.
                        song.countIn.pickUpOnBeat = userInputFloat
                        editValid = True
                    else:
                        editValid = False
                except ValueError:
                        editValid = False
            case 3:
                userInput = input('ENTER Count on Half-Beat? Y/N: ')
                match userInput.lower():
                    case "y":
                        song.countIn.halfBeatCount = True
                        editValid = True
                    case "n":
                        song.countIn.halfBeatCount = False
                        editValid = True
                    case _:
                        editValid = False
            case 4:
                userInput = input('ENTER New Key Signature: ')
                if self._interact_Validate_KeySignature(userInput) == True:
                    song.key = userInput
                    editValid = True
                else:
                    editValid = False
            case 5:
                userInput = input("ENTER New Time Signature (e.g., 3/4): ")
                valid, num, dem = self._interact_Validate_TimeSignature(userInput)
                if valid:
                    song.timeSigNum = num
                    song.timeSigDen = dem
                    song.tempoMIDI = mido.bpm2tempo(song.tempoBPM, time_signature=(song.timeSigNum,song.timeSigDen))
                    song.set_SongLength_Seconds()
                    print(f"Song Len Seconds = {song.songLengthSeconds}")
                    editValid = True
                else:
                    editValid = False
            case 6:
                userInput = input('ENTER Number of Full Play-Throughs of the Original Song to Add to the Output MIDI File: ')
                if userInput.isdigit():
                    song.playThroughs = int(userInput)
                    editValid = True
                else:
                    editValid = False
        print(self.hlOFF, end="")
        return editValid


    def _interact_EditTrack(self, song, trackIdxToEdit):
        """ Description: Handle user interaction for song track editing.
        Param:  userInput - What user entered at confirm specs prompt. May or may not be valid.
        Param:  song - Instance of the Song class.
        Doc:    See doc_UML.odg
        """
        specsOK = False
        retry = False #     <-- Used to show a 'input is invalid, try again' message to user in _getUserEditChoice() when True
        #
        #---- Don't go into editing loop if trackIdxToEdit is out of validity range
        if 0 <= trackIdxToEdit < (len(song.trackInfo)-1): # <-- Don't allow editing of count-in track
            #
            #----- Loop Until User Confirms Specs or Requests to Quit
            while specsOK == False:
                #
                #---- Put Display on Screen
                display.clearScreen()
                display.songHeader()
                display.songInfo(song, blankLines=0, forConfirm=False)
                display.sepLine(0,0,'-')
                display.trackList(song, False, trackIdxToEdit)
                #
                #----- Get User Input
                retry, group, numberVal = self._getUserEditChoice(retry)
                match group:
                    case 'P':
                        retry = not self._interact_EditTrackParam(song, trackIdxToEdit, numberVal) # <-- Returns False if there is invalid user input
                    case "C":
                        retry = False
                        specsOK = True #                                                              <-- Only exit from loop is when user tells us to 'c'-continue
                    case _:
                        retry = True
                        specsOK = False
        return specsOK


    def _interact_EditTrackParam(self, song, trackIdx, paramIndex):
        """ Description: Handle user interaction for editing a track's parameters.
        Param:  song - Instance of the Song class.
        Param:  paramIndex - the index number of the editable track param as seen by the user.
                Note that the code logic prevents editing of the Keep/Remove param of track-0.
        Note:   The paramIndex is tied to the case statements directly. Not elegant.
        """
        editValid = False
        print(self.hlON, end="")
        match paramIndex:
            case 1:
                userInput = input('ENTER Track Name: ')
                if userInput and len(userInput) < 101:
                    song.trackInfo[trackIdx][TI_NAME] = userInput.strip()
                    editValid = True
                else:
                    editValid = False
            case 2:
                userInput = input('ENTER New Key Signature: ')
                userInput = userInput.upper()
                if self._interact_Validate_KeySignature(userInput) == True:
                    song.trackInfo[trackIdx][TI_KEY] = userInput
                    editValid = True
                else:
                    editValid = False
            case 3:
                if trackIdx == 0: # <-- Do not permit Track-0 to be removed
                    editValid = False
                else:
                    userInput = input('Keep Track? Y/N: ')
                    match userInput.lower():
                        case "y":
                            song.trackInfo[trackIdx][TI_KEEP] = True
                            editValid = True
                        case "n":
                            song.trackInfo[trackIdx][TI_KEEP] = False
                            editValid = True
                        case _:
                            editValid = False
        print(self.hlOFF, end="")
        return editValid


    def _interact_Validate_KeySignature(self, keySig):
        pattern = r'^[A-G][#b]?m?$' # <- # Define a regular expression pattern for valid key signatures
        if re.match(pattern, keySig): # <- # Use re.match to check if the input matches the pattern
            return True
        else:
            return False

    def _interact_Validate_TimeSignature(self, timeSig):
        pattern = r'^(\d+)\/(\d+)$'
        match = re.match(pattern, timeSig)
        if match:
            num, dem = map(int, match.groups())
            if 1 < num < 17 and 1 < dem < 17:
                return True, num, dem
            else:
                return False, 0, 0
        else:
            return False, 0, 0


    def _files_Valid(self):
        """ PRIVATE FUNCTION
            This function validates input & output file paths.
            NOTE: - If user does not provide an argument for the output file, OR provides only the
        name of a file with no path spec, then we have an empty string for the path to the
        output file. In a test for valid path this returns False. So we test for this
        condition and if it is the case we pre-pend the current working directory.
            RETURNS 0 if both are valid, -1 if input file is invalid, -2 if output path is invalid."""
        if not os.path.isfile(self.args.input_file_path):
            errHandler.set_Error(1)
            return False
        if len(os.path.dirname(self.args.output_file_path)) == 0:
            self.args.output_file_path = os.path.join(os.getcwd(), os.path.basename(self.args.output_file_path)) # <- current working directory + default string of the -o command line argument.
            #print(f"Output File Path: {args.output_file_path}")
        if not os.path.dirname(self.args.output_file_path):
            errHandler.set_Error(2)
            return False
        return True


    def _extractIntegerFromString(self, stringWithNumber):
        match = re.search(r'\d+', stringWithNumber)
        if match:
            numberStr = match.group(0)
            number = int(numberStr)
        else:
            number = -1
        return number



# =================================================================================================
#    Main Thread of Code (which is in effect is also the 'Controller' in MVC terms)
# =================================================================================================
#
# ---- Instantiate class instances and do set-up work
errHandler = errorHandler()
display = TerminalDisplay()
ui=UserInterface()
ui.input_commandline()                                      # <-- Get the command line arguments user entered
errHandler.handleError()                                    # <-- IF a fatal error in process we exit. If no error nothing happens
song = Song(ui.args.input_file_path,ui.args.output_file_path)
song.populate_SongInfo()
#
# ---- Handle case for info display only, no count-in to be added
if ui.args.info_only == True:
    display.songHeader()
    display.songInfo(song, 0, False)
    display.sepLine(0,1, '-')
    display.track_namesForFile(song.sourceMIDI, "Input MIDI File")
    for track in song.sourceMIDI.tracks:
        display.track_MessagesMeta(track)
    display.track_messagesForFile(song.sourceMIDI, "Input MIDI File")
    sys.exit(0)
#
# ---- If we got here user wants to add a count-in
confirmSpecs = ui.interact_ConfirmSpecs(display, song)
if confirmSpecs != True:
    sys.exit(1)
#
#---- We have what we need, go ahead and produce the output MIDI file
print('\n***** GENERATING OUTPUT MIDI WITH COUNT-IN *****')
song.build_outputMidi()
#
#---- Save output MIDI file to disk
#    NOTE: The mido.MidiFile.filename param is NOT populated after a file save. The file is saved
#          just fine, but that param is not updated with the file save. Just something to note.
song.write_outputFile()
#
#---- We're Done
display.progressMessage(f"COUNT-IN ADDED - Result is in File: {song.outputMIDI.outFilePath}")
