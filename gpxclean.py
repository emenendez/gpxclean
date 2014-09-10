#!/usr/local/bin/python3

import argparse
import gpxpy
import gpxpy.gpx
from pathlib import Path
import string
import sys

parser = argparse.ArgumentParser(description='Clean GPX tracks and split into multiple files.')
parser.add_argument('-s', '--split', type=int, default=300, help='Split tracks if points are greater than this distance apart (meters).')
parser.add_argument('-T', '--time', action='store_true', dest='time', help='Use time in output filenames (default).')
parser.add_argument('-t', '--no-time', action='store_false', dest='time', help='Do not use time in output filenames.')
parser.add_argument('-N', '--name', action='store_true', dest='name', help='Use track/waypoint name in output filenames.')
parser.add_argument('-n', '--no-name', action='store_false', dest='name', help='Do not use track/waypoint name in output filenames (default).')
parser.add_argument('-l', '--max-filename-length', type=int, dest='length', default=50, help='Warn if output filename is longer than this number of characters.')
parser.add_argument('input', nargs='+', help='a .gpx file to clean and split')
parser.set_defaults(time=True, name=False)
args = parser.parse_args()


def makePath(base_name, i):
    if i == 0:
        return Path('{}.gpx'.format(base_name))
    else:
        return Path('{}_{:03d}.gpx'.format(base_name, i))

def createUniqueFile(base_name, time=None, name=None):
    i = 0
    file_name = base_name
    if args.time and time:
        file_name += '_' + time.strftime('%Y-%m-%d %H.%M.%S')
    if args.name and name:
        file_name += '_' + name
    
    # Create valid filename
    file_name = file_name.replace('(', '').replace(')', '')  # Remove parens
    valid_chars = '-_. {}{}'.format(string.ascii_letters, string.digits)
    file_name = ''.join(c if c in valid_chars else '-' for c in file_name)

    while makePath(file_name, i).exists():
        i += 1

    file_name = makePath(file_name, i)
    if args.length != 0 and len(str(file_name)) > args.length:
        print('Warning: {} greater than {} characters.'.format(file_name, args.length), file=sys.stderr)

    return file_name

def writeAndCreateNewFile(segment, base_name, track_name=None):
    if segment is not None and segment.get_points_no() > 1:
        # Create new GPX file
        gpx = gpxpy.gpx.GPX()

        # Create first track in our GPX:
        track = gpxpy.gpx.GPXTrack(name=track_name)
        gpx.tracks.append(track)

        # Add segment to our GPX track:
        track.segments.append(segment)
        
        time = segment.get_time_bounds().start_time
        outfile = createUniqueFile(base_name + '_track', time, track_name)
        with outfile.open('w') as output:
            output.write(gpx.to_xml())
    
    # Return a new segment
    return gpxpy.gpx.GPXTrackSegment()

def writeWaypoint(waypoint, base_name):
    if waypoint:
        # Create new GPX file
        gpx = gpxpy.gpx.GPX()

        # Append waypoint
        gpx.waypoints.append(waypoint)

        outfile = createUniqueFile(base_name + '_waypoint', waypoint.time, waypoint.name)
        with outfile.open('w') as output:
            output.write(gpx.to_xml())


new_segment = None
current_track_name = None

for infile in args.input:
    infile = Path(infile)
    with infile.open() as gpx_file:
        gpx = gpxpy.parse(gpx_file)

        # Extract tracks
        for track in gpx.tracks:
            for segment in track.segments:
                # Create new segment, and write out the current one
                new_segment = writeAndCreateNewFile(new_segment, infile.stem, current_track_name)
                current_track_name = track.name

                previous_point = None
                for point in segment.points:
                    if previous_point:
                        if point.distance_2d(previous_point) > args.split:
                            # Start new segment
                            new_segment = writeAndCreateNewFile(new_segment, infile.stem, current_track_name)
                            
                    previous_point = point
                    new_segment.points.append(point)
        # Write final segment
        new_segment = writeAndCreateNewFile(new_segment, infile.stem, current_track_name)

        # Extract waypoints
        for waypoint in gpx.waypoints:
            writeWaypoint(waypoint, infile.stem)
