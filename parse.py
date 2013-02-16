#!/usr/bin/env python
# -*- coding:utf-8

import sys
import argparse
import math
import numpy


class Session:
    def __init__(self, line, nbin):
        self.line = line
        self.nbin = nbin
        self.parseLine(line, nbin)

    @property
    def metadata(self):
        return [
            self.project, self.userid, self.protocol, self.session,
            self.station, self.run, self.subject, self.rundate, self.runtime   
        ]

    def parseLine(self, line, nbin):
        '''Parse and sanitize a line read from a file
        (converting fields to integers if possible)
        '''
        columns = line.strip().split('\t')
        self.project, self.userid, self.protocol, self.session, \
                self.station, self.run, self.subject, self.rundate, \
                self.runtime = map(tryInt, columns[:9])
        session = map(tryInt, columns[9:])
        self.essays = {}
        for i, bin in enumerate(session):
            e = i / nbin
            if e in self.essays:
                self.essays[e].append(bin)
            else:
                self.essays[e] = [bin]

    def meansBin(self, factor=1, normActivity=False):
        means = []
        for i in range(self.nbin):
            means.append(numpy.mean([v[i] for v in self.essays.values()]) / factor)
        if normActivity:
            means = numpy.array(means) / self.meanActivity
        return list(means)

    def meanActivity(self, factor=1):
        return numpy.mean(self.meansBin(factor))

    def smooth(self, step=1, wdw=2, factor=1):
        output = []
        data = list(numpy.array(self.meansBin(factor)) / self.meanActivity(factor))
        for pos in range(0, len(data), step):
            output.append(numpy.mean(data[pos:pos + wdw]))
        return output



class SessionsSet(list):
    def __init__(self, sessions=[]):
        super(SessionsSet, self).__init__(sessions)
    
    def meanMeansBin(self, factor=1):
        output = numpy.zeros( len(self[0].meansBin(factor)) )
        for session in self:
            output += numpy.array(session.meansBin(factor))
        output /= len(self)
        return list(output)

    def meanMeanActivity(self, factor=1):
        output = 0
        for session in self:
            output += session.meanActivity(factor)
        output /= len(self)
        return output

    def meanSmooth(self, step=1, wdw=2, factor=1):
        output = numpy.zeros( len(self[0].smooth(step, wdw, factor)) )
        for session in self:
            output += numpy.array(session.smooth(step, wdw, factor))
        output /= len(self)
        return list(output)

    def semSmooth(self, step=1, wdw=2, factor=1):
        output = []
        for ibin in zip(*[s.smooth(step, wdw, factor) for s in self]):
            output.append(sem(ibin))
        return output


def tryInt(value):
    try:
        return int(value)
    except:
        return value


def sem(array):
    return numpy.std(array) / math.sqrt(len(array))


def eta_squared(ref, c):
    """Calcule l'eta2, soit la superposition des courbes, entre deux
lignes de données
    Admet 2 arguments, soit 2 lignes de tableau : la ligne du tableau
servant de référence et la ligne à comparer """
    mysum=sum([(ref[k]+c[k])**2 for k in range(len(ref))])
    snorm=sum([ref[k]**2+c[k]**2 for k in range(len(ref))])
    sNorm_square = (sum(ref)+sum(c))**2/(len(ref)+len(c))
    sst = mysum/2 - sNorm_square
    sstot = snorm - sNorm_square
    eta2 = sst/sstot
    return eta2


def main(args):

    # Iterate over each line of the given file object and create Session objects
    sessions = SessionsSet()
    for line in args.infile:
        if not line.strip().startswith('Project'):
            sessions.append(Session(line, args.nbin))
    
    if args.subcmd == 'meansBin':
        for session in sessions:
            output = session.metadata + session.meansBin(factor=args.factor)
            print >>args.outfile, '\t'.join(map(str, output))
    if args.subcmd == 'meanActivity':
        for session in sessions:
            output = session.metadata + session.meanActivity(factor=args.factor)
            print >>args.outfile, '\t'.join(map(str, output))
    if args.subcmd == 'meanMeansBin':
        output = sessions.meanMeansBin(factor=args.factor)
        print >>args.outfile, '\t'.join(map(str, output))
    if args.subcmd == 'meanMeanActivity':
        res = sessions.meanMeanActivity(factor=args.factor)
        print >>args.outfile, res
    if args.subcmd == 'smooth':
        for session in sessions:
            output = session.metadata + session.smooth(step=args.step, wdw=args.window, factor=args.factor)
            print >>args.outfile, '\t'.join(map(str, output))
    if args.subcmd == 'meanSmooth':
        output = sessions.meanSmooth(step=args.step, wdw=args.window, factor=args.factor)
        print >>args.outfile, '\n'.join(map(str, output))

    #exp_ids = [1, 3, 7, 2, 4, 6]
    #ctrl_ids = [5, 9, 11, 8, 10, 12]

    #exp_sessions = SessionsSet([s for s in sessions if s.subject in exp_ids])
    #ctrl_sessions = SessionsSet([s for s in sessions if s.subject in ctrl_ids])

    #data_exp = zip(exp_sessions.meanSmooth(factor=2), exp_sessions.semSmooth(factor=2), ['experimental']*60)
    #data_ctrl = zip(ctrl_sessions.meanSmooth(factor=2), ctrl_sessions.semSmooth(factor=2), ['control']*60)

    #for dataset in [data_ctrl, data_exp]:
        #for i in dataset:
            #print '\t'.join(map(str, i))
    #for session in sessions:
        #output = session.metadata + session.smooth(factor=2)
        #print '\t'.join(map(str, output))



if __name__ == '__main__':

    # Base parser, for file and global options
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument(
        '-i', '--infile', dest='infile',
        type=argparse.FileType('r'),
        default=sys.stdin,
        help='Input file'
    )
    base_parser.add_argument(
        '-o', '--outfile', dest='outfile',
        type=argparse.FileType('w'),
        default=sys.stdout,
        help='Output file'
    )
    base_parser.add_argument(
        '-n', '--nbin', dest='nbin',
        type=int,
        default=60,
        help='Number of bins'
    )
    base_parser.add_argument(
        '-f', '--factor', dest='factor',
        type=int,
        default=1,
        help='Factor to apply to each bin'
    )

    # Smooth parser for smoothing specific options
    smooth_parser = argparse.ArgumentParser(add_help=False)
    smooth_parser.add_argument(
        '-s', '--step', dest='step',
        type=int,
        default=1,
        help='Step'
    )
    smooth_parser.add_argument(
        '-w', '--window', dest='window',
        type=int,
        default=2,
        help='Window size'
    )

    # Main parser
    parser = argparse.ArgumentParser(parents=[base_parser])
    
    # Sub-parsers
    subparsers = parser.add_subparsers(
        title='subcommands',
        dest='subcmd'
    )
    parser_meansBin = subparsers.add_parser(
        'meansBin',
        parents=[base_parser],
        help='Compute the means in each bin across trials'
    )
    parser_meanActivity = subparsers.add_parser(
        'meanActivity',
        parents=[base_parser],
        help='Compute the activity associated to each subject'
    )
    parser_meanMeansBin = subparsers.add_parser(
        'meanMeansBin',
        parents=[base_parser],
        help='Compute the mean of meansBin across subjects'
    )
    parser_meanMeanActivity = subparsers.add_parser(
        'meanMeanActivity',
        parents=[base_parser],
        help='Compute the mean of activities across subjects'
    )
    parser_smooth = subparsers.add_parser(
        'smooth',
        parents=[base_parser, smooth_parser],
        help='Compute the smoothed means in each bin across trials'
    )
    parser_meanSmooth = subparsers.add_parser(
        'meanSmooth',
        parents=[base_parser, smooth_parser],
        help='Compute the mean of smoothed meanBins across subjects'
    )

    main(parser.parse_args())
