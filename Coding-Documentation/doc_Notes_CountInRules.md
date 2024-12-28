# Notes on the Rules for the Count In Sequence

The following information serves as the basis, and logic, behind the coding for generating the count-in.

## Limitations

In doing an internet search I can see there are a variety of differing opinions and conventions in use for counting in. Note that this program provides some degree of control for how to sequence your count-in, but it is pretty limited, based on the below documented rules and cases (to keep complexity under control). As one example, many musicians and conductors think of 6/8 time as 2 groups of triplets and conduct it in "2" instead of 6. This program does not have the ability to specify this variant. The rules and cases described below are what have been used to derive the coding logic and thus it will be helpful to understand these in order to make effective use of the program.

## Full Measure Counts

A full measure of count-in is straight-forward and obvious.

**Full Beat Count**. A 'full beat' count is one sound (note) for each beat as defined by the time signature's denominator. 

*Example-1*: 4/4 time gets a 'count' sound every quarter note. As in: " 1 2 3 4". 

*Example-2*: 6/8 time yields: "1 2 3 4 5 6".

**Half-Beat Count**. A 'half beat' count is two sounds (notes) for each beat as defined by the time signature's denominator. 

*Example-1*: 4/4 time gets a 'count' sound every 8th note: "1 & 2 & 3 & 4 &".

*Example-2*: 6/8 time yields: "1 & 2 & 3 & 4 & 5 & 6 &".

## Pick-Up Measure Counts

A pickup measure, as we all know, is a partial measure that begins a song. For example, a tune in 4/4 time may begin with a single quarter note in it's first measure. So it begins with a one-beat measure instead of a fully populated, 4-beat measure. That's a so-called "pickup measure."

### Case-1: First Pickup Note on Full Beat, Request Full-Beat Count

Say the pickup measure's first note is a full beat duration note,  as defined by the time signature's denominator, and it starts at the final beat in the pickup measure. Further assume that you did **not** specify to use Half-Beat counts.

*Example-1*: 4/4 time with a single quarter note pickup. Count-In: "1 2 3 4 | 1 2 3"

*Example-2*: 6/8 time with two 8th notes in the pickup. Count-In: "1 2 3 4 5 6 | 1 2 3 4"

*Example-3*: 3/4 time with a pickup that contains 2 beats, one quarter note followed by 2 eighth notes. “1 & 2 & 3 & | 1 &”

### Case-2: First Pickup Note on Full Beat, Request Half-Beat Count

Now assume that the pickup measure's first note is a full beat duration note as defined by the time signature's denominator, **and you specified to use Half-Beat counts**.

*Example-1*: 4/4 time with a single full beat duration pickup note. You get: "1 & 2 & 3 & 4 & | 1 & 2 & 3 &"

*Example-2*: 6/8 time with three 8th note pickups. You get: "1 & 2 & 3 & 4 & 5 & 6 & | 1 & 2 & 3 &"

*Example-3*: 3/4 time with a pickup that contains one quarter note followed by 2 eighth notes. "1 & 2 & 3 & | 1 &"

### Case-3: First Pickup Note on Half Beat, Request Full-Beat Count

Now say that the pickup measure's first note is of a half beat duration as defined by the time signature's denominator and that you did **not** specify to use Half-Beat counts. If the pickup begins on a half-beat then you may want to consider opting for a half-beat count-in sequence. Sticking with a Full-Beat count with a Half-Beat final pickup note I am using this convention: The count looks the same as for case-1 above, and player know to play the half-beat note as soon as they hear the final counting number. Of course the duration of this final counting sound will be a half-beat to sync with the true start of the song.

*Example-1*: 4/4 time with a single 8th note pickup. You get: "1 2 3 4 | 1 2 3 4" <-- The "4" tho sounds for only a half-beat so that the song's pickup note comes in on proper time.

*Example-2*: 6/8 time with a pickup that contains one 16th note followed by 2 eighth notes. You then get: "1 2 3 4 5 6 | 1 2 3 4" <-- Again, this '4' will be the duration of a 16th note. (Just giving this example to make the rules I have programmed into the script clear. In real-life a song with this starting pattern would probably be counted-in using some pattern that made sense to the players in their own context and experience. My program does not, and cannot, account for all cases given the complexity of real-life music, so in some edge cases you'd need to just set the count-in parameters to give you a least-worst-case.)

### Case-4: First Pickup Note on Half Beat, Request Half-Beat Count

OK, let's say that the pickup measure's first note is of a half beat duration as defined by the time signature's denominator and that it starts on a half-beat point in the pickup measure. Further say that you went ahead and specified to use Half-Beat counts.

*Example-1*:  4/4 time with a single 8th note pickup. You get: "1 & 2 & 3 & 4 & | 1 & 2 & 3 & 4"

*Example-2*: 6/8 time with a pickup that contains one 16th note followed by 2 eighth notes. You then get: "1 & 2 & 3 & 4 & 5 & 6 & | 1 & 2 & 3 & 4"

### Pickup Logic Table

Given the above defined cases, below is the logic table for specifying the pickup measure's count-in sequence:

| Case | Pickup Begins On | Full Ct / Half Ct | Example - 4/4 time             |
| ---- | ---------------- | ----------------- | ------------------------------ |
| 1    | Full Beat (4)    | Full Ct           | 1-2-3-4 \| 1-2-3               |
| 2    | Full Beat (4)    | Half Ct           | 1-&-2-&-3-&-4-&\|1-&-2-&-3-&   |
| 3    | Half Beat (4.5)  | Full Ct           | 1-2-3-4 \| 1-2-3-4             |
| 4    | Half Beat (4.5)  | Half Ct           | 1-&-2-&-3-&-4-&\|1-&-2-&-3-&-4 |


### Coding Notes

From the above: In order to unambiguously spec the pick-up count-in I have to use the first two columns. Meaning that I need the user to tell the script **what beat the first pickup note begins on** - *which could be a fractional beat*. Then from the user having accepted the default 'Full Beat Count,' or edited the parms to specify 'Half-Beat Counts,' we have the two pieces of information we need to produce the desired count-in sequence for the pickup measure.
