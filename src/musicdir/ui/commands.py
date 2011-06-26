# This file is part of musicdir.
# Copyright 2011, coolkehon.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

from musicdir import ui

# The list of default subcommands. This is populated with Subcommand
# objects that can be fed to a SubcommandsOptionParser.
default_commands = []

# {{{ list: Query and show library contents.
def list_items(lib, query, release, path):
    """Print out items in lib matching query. If album, then search for
    albums instead of single items. If path, print the matched objects'
    paths instead of human-readable information about them.
    """
    if release:
        for rls in lib.releases(query):
            if path:
                print_(rls.dirpath)
            else:
                print_(lib.artist(rls.artist).name + u' - ' + rls.name)
    else:
        for track in lib.tracks(query):
            if path:
                print_(track.path)
            else:
                print_(lib.artist(track.artist).name + u' - ' + lib.release(track.release).name + u' - ' + track.title)

list_cmd = ui.Subcommand('list', help='query the library', aliases=('ls',))
list_cmd.parser.add_option('-r', '--release', action='store_true',
    help='show matching releases instead of tracks')
list_cmd.parser.add_option('-p', '--path', action='store_true',
    help='print paths for matched items or albums')
def list_func(lib, config, opts, args):
    list_items(lib, ui.make_query(args), opts.release, opts.path)
list_cmd.func = list_func
default_commands.append(list_cmd)
# }}} end list: Query and show library contents

# {{{ import: simple import into library
import_cmd = ui.Subcommand('import', help='import new music',
    aliases=('imp', 'im'))
import_cmd.parser.add_option('-c', '--copy', action='store_true',
    default=None, help="copy tracks into library directory (default)")
import_cmd.parser.add_option('-C', '--nocopy', action='store_false',
    dest='copy', help="don't copy tracks (opposite of -c)")
import_cmd.parser.add_option('-w', '--write', action='store_true',
    default=None, help="write new metadata to files' tags (default)")
import_cmd.parser.add_option('-W', '--nowrite', action='store_false',
    dest='write', help="don't write metadata (opposite of -w)")
import_cmd.parser.add_option('-a', '--autotag', action='store_true',
    dest='autotag', help="infer tags for imported files (default)")
import_cmd.parser.add_option('-A', '--noautotag', action='store_false',
    dest='autotag',
    help="don't infer tags for imported files (opposite of -a)")
import_cmd.parser.add_option('-p', '--resume', action='store_true',
    default=None, help="resume importing if interrupted")
import_cmd.parser.add_option('-P', '--noresume', action='store_false',
    dest='resume', help="do not try to resume importing")
import_cmd.parser.add_option('-r', '--art', action='store_true',
    default=None, help="try to download album art")
import_cmd.parser.add_option('-R', '--noart', action='store_false',
    dest='art', help="don't album art (opposite of -r)")
import_cmd.parser.add_option('-q', '--quiet', action='store_true',
    dest='quiet', help="never prompt for input: skip albums instead")
import_cmd.parser.add_option('-l', '--log', dest='logpath',
    help='file to log untaggable albums for later review')
import_cmd.parser.add_option('-s', '--singletons', action='store_true',
    help='import individual tracks instead of full albums')
import_cmd.parser.add_option('-t', '--timid', dest='timid',
    action='store_true', help='always confirm all actions')

def import_func(lib, config, opts, args):
    pass
import_cmd.func = import_func
default_commands.append(import_cmd)
# }}}
