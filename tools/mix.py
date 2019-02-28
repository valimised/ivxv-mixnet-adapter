#!/usr/bin/env python2

# Copyright (C) 2019 State Electoral Office
#
# This file is part of ivxv-verificatum.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License
# for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import asn1
import base64
import logging
import os
import subprocess
import sys
import tempfile
import time
import zipfile

VERCP = ["verificatum-vcr.jar", "verificatum-vcr-vmgj.jar",
         "verificatum-vmn.jar", "verificatum-vmgj.jar"]
IVXVCP = ["ivxv-common-all.jar", "ivxv-common.jar", "ivxv-verificatum.jar"]
CP = VERCP + IVXVCP
WIDTH = 1
KEYWIDTH = 5
ENTROPY_THRES = 40

log = logging.getLogger("runner")
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s %(message)s')


def random_source():
    return os.path.expanduser("~/.verificatum_random_source")


def random_seed():
    return os.path.expanduser("~/.verificatum_random_seed")


def pid():
    return "{}".format(os.getpid())


def get_env():
    libdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../lib")
    return {"CLASSPATH": ":".join(map(
        lambda x: os.path.abspath(os.path.join(libdir, x)), CP)),
        "LD_LIBRARY_PATH": libdir
    }


def get_width():
    return "{}".format(WIDTH)


def get_keywidth():
    return "{}".format(KEYWIDTH)


def vog(args):
    return [
        "java",
        "-d64",
        "-Djava.security.egd=file:/dev/./urandom",
        "com.verificatum.ui.gen.GeneratorTool",
        "vog",
        ":VERIFICATUM_VOG_BUILTIN",
        random_source(),
        random_seed(),
    ] + args


def vmnv(args):
    return [
        "java",
        "-server",
        "-d64",
        "-Xmx3000m",
        "-Djava.security.egd=file:/dev/./urandom",
        "com.verificatum.protocol.mixnet.MixNetElGamalVerifyFiatShamirTool",
        "vmnv",
        random_source(),
        random_seed(),
    ] + args


def vmni(args):
    return [
        "java",
        "-d64",
        "-Djava.security.egd=file:/dev/./urandom",
        "com.verificatum.ui.info.InfoTool",
        "vmni",
        random_source(),
        random_seed(),
        "com.verificatum.protocol.mixnet.MixNetElGamal",
    ] + args


def vmnc(args):
    return [
        "java",
        "-d64",
        "-Xmx3000m",
        "-Djava.security.egd=file:/dev/./urandom",
        "com.verificatum.protocol.elgamal.ProtocolElGamalInterfaceTool",
        "vmnc",
        "com.verificatum.protocol.mixnet.MixNetElGamalInterfaceFactory",
        random_source(),
        random_seed(),
    ] + args


def vmn(args):
    return [
        "java",
        "-d64",
        "-Xmx3000m",
        "-Djava.security.egd=file:/dev/./urandom",
        "com.verificatum.protocol.mixnet.MixNetElGamalTool",
        pid(),
        "vmn",
    ] + args


def parse_key(pubkey):
    pem = open(pubkey).readlines()[1:-1]
    der = base64.decodestring("".join(pem))
    a = asn1.parse_der(der)
    P = a[0][0][1][0].value.encode('hex')
    G = a[0][0][1][1].value.encode('hex')
    election = a[0][0][1][2].value
    filtered_election = filter_election_id(election)
    log.debug("parsed public key")
    log.debug("P = %s\nG = %s\nelection_id = %s\nfiltered_id = %s", P, G,
              election, filtered_election)
    return (filtered_election, (P, G))


def filter_election_id(election):
    first = range(ord('a'), ord('z')) + range(ord('A'), ord('Z'))
    second = first + range(ord('0'), ord('9')) + [ord('_'), ord(' ')]
    first, second = map(chr, first), map(chr, second)
    repl = '_'
    ret = list(election)
    if len(ret) == 0:
        return ''
    if ret[0] not in first:
        ret[0] = repl
    if len(ret) == 1:
        ret += [repl]
    for i in range(1, len(ret[1:])):
        if ret[i] not in second:
            ret[i] = repl
    return "".join(ret)[:256]


def remove_old_source_and_seed():
    log.debug("removing random source and seed")
    try:
        os.remove(random_source())
        log.debug("removed old random source")
    except OSError:
        # does not exist
        pass
    try:
        os.remove(random_seed())
        log.debug("removed old random seed")
    except OSError:
        # does not exist
        pass


def write_seed(election):
    f = tempfile.NamedTemporaryFile()
    towrite = election.encode('hex')
    f.file.write(towrite)
    f.file.write((64-len(towrite)) * "0")
    f.file.flush()
    log.debug("wrote seed to %s", f.name)
    return f


def generate_randomsource():
    hashfn = run(vog("-gen HashfunctionHeuristic SHA-256".split()))
    prg = run(vog(["-gen", "PRGHeuristic", hashfn]))
    urandom = run(vog("-gen RandomDevice /dev/urandom".split()))
    return [prg, urandom]


def empty_entropy_pool():
    log.debug("emptying entropy pool")
    f = open("/dev/random", "rb", 0)
    while current_entropy_level() > ENTROPY_THRES:
        f.read(1)
    log.debug("entropy pool emptied")


def block_until_entropy(amount):
    os.system("stty -echo")
    lastlevel = 0
    log.info("Current entropy level %d/%d", lastlevel, amount*8)
    while current_entropy_level() < amount*8 + ENTROPY_THRES:
        if current_entropy_level() > lastlevel + 160:
            lastlevel = current_entropy_level()
            log.info("Current entropy level %d/%d", lastlevel, amount*8)
        time.sleep(0.1)
    os.system("stty echo")
    log.debug("entropy pool filled")


def current_entropy_level():
    return int(open("/proc/sys/kernel/random/entropy_avail").read())


def run(args):
    log.debug("running cmd: %s", " ".join(args))
    ret = subprocess.check_output(args, env=get_env())
    log.debug("cmd output: %s", ret)
    return ret


def pack_proof(zip, pubkey, ballots, shuffled):
    z = zipfile.ZipFile(zip, "w", allowZip64=True)
    z.write("prot.xml")
    z.write(pubkey, "Publickey.pem")
    z.write(ballots, "BallotBox.json")
    z.write(shuffled, "ShuffledBallotBox.json")
    for p in ["auxsid", "Ciphertexts.bt", "FullPublicKey.bt",
              "ShuffledCiphertexts.bt", "type", "version", "width"]:
        z.write(os.path.join("dir/nizkp/default", p),
                os.path.join("mixnet", p))
    for p in ["activethreshold", "Ciphertexts01.bt",
              "PermutationCommitment01.bt", "PoSCommitment01.bt",
              "PoSReply01.bt"]:
        z.write(os.path.join("dir/nizkp/default/proofs", p),
                os.path.join("mixnet/proofs", p))
    template = "mixer:\n  protinfo: prot.xml\n  proofdir: mixnet/\n"
    z.writestr("conf.yaml", template)
    z.close()


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Runner script for running Verificatum mix-net")
    parser.add_argument("command", choices = ['shuffle', 'verify'],
                        help="Action to take")
    parser.add_argument("--pubkey",
                        help="Location of the public key in PEM format")
    parser.add_argument("--ballotbox",
                        help="Location of the ballot box to be shuffled")
    parser.add_argument("--shuffled",
                        help="Output location of the shuffled ballot box")
    parser.add_argument("--no-user-entropy",
                        help="Omit cleaning entropy pool and requesting "
                        "entropy from the user (for automated testing)",
                        action="store_true")
    parser.add_argument("--proof-zipfile",
                        help="Add all artefacts for verifying the "
                        "correctness of shuffle to a zip file. "
                        "Additionally, construct a configuration file "
                        "for IVXV auditor application")
    parsed = parser.parse_args(argv)
    return parsed


def mix(pubkey, bbox, out, skipentropy=False):
    log.info("Parsing public key")
    election, params = parse_key(pubkey)
    # remove old .verificatum_random_source and .verificatum_random_seed
    log.info("Removing previous Verificatum seed and random source")
    remove_old_source_and_seed()
    # create tmpfile, write election_id in hex-encoded into it (long enough)
    log.info("Writing seed to temporary file")
    seedfile = write_seed(election)
    # generate Verificatum random source description
    log.info("Generating random source description")
    prg_desc, urandom_desc = generate_randomsource()
    combined_desc = run(vog(["-gen", "PRGCombiner", prg_desc, urandom_desc]))
    # run rndinit to initialize Verificatum random source
    log.info("Initializing Verificatum random source")
    run(vog(["-rndinit", "-seed", seedfile.name, "PRGCombiner", prg_desc,
             urandom_desc]))
    if not skipentropy:
        # read /dev/random until empty
        log.info("Emptying entropy pool")
        empty_entropy_pool()
        # poll /proc/sys/kernel/random/entropy_avail until >1024
        log.info("Collecting user entropy")
        log.info("Add input. Terminal echo is turned off for the stage")
        block_until_entropy(128)
    else:
        log.info("Skipping entropy pool emptying and collection from user")
    log.info("Generating ElGamal group parameters for Verificatum")
    pgroup = run(vog("-gen ModPGroup -explic {} {}".
                     format(params[0], params[1]).split()))
    log.info("Generating Verificatum protocol stub file")
    run(vmni(["-prot", "-sid", "ivxv", "-name", election, "-keywidth",
             get_keywidth(), "-width", get_width(), "-nopart", "1", "-thres",
             "1", "-pgroup", pgroup, "stub.xml"]))
    log.info("Generating Verificatum party protocol file")
    run(vmni(["-party", "-name", "Party", "-rand", combined_desc, "-seed",
              seedfile.name, "stub.xml", "privInfo.xml", "protInfo.xml"]))
    log.info("Merging Verificatum protocol file")
    run(vmni("-merge protInfo.xml prot.xml".split()))
    log.info("Converting IVXV public key to Verificatum format")
    run(vmnc("-pkey -ini ee.ivxv.verificatum.Adapter -outi raw prot.xml {} publickey".format(pubkey).split()))
    log.info("Setting Verificatum public key")
    run(vmn("-setpk privInfo.xml prot.xml publickey".split()))
    log.info("Converting IVXV ballot box to Verificatum ciphertexts")
    run(vmnc("-ciphs -ini ee.ivxv.verificatum.Adapter -outi raw prot.xml {} ciphertexts".format(bbox).split()))
    log.info("Shuffling ciphertexts")
    run(vmn("-e -shuffle privInfo.xml prot.xml ciphertexts shuffled".split()))
    log.info("Converting Verificatum ciphertexts to IVXV ballot box")
    run(vmnc("-ciphs -ini raw -outi ee.ivxv.verificatum.Adapter prot.xml shuffled {}".format(out).split()))
    log.debug("Closing seed file")
    seedfile.close()


def verify(proofzip):
    import zipfile
    log.info("Verifying correctness of the shuffle")
    with zipfile.ZipFile(proofzip) as myzip:
        myzip.extractall()
    run(vmnv("-shuffle prot.xml mixnet".split()))
    log.info("Shuffle verified!")


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    log.debug("Parsed arguments: {}".format(args))
    log.debug("Script started")

    if args.command == 'verify':
        verify(args.proof_zipfile)
    else:
        mix(args.pubkey, args.ballotbox, args.shuffled,
            skipentropy=args.no_user_entropy)
        log.info("Mixing finished.  Shuffled ballot box is located at {}".
                 format(args.shuffled))
        if args.proof_zipfile is not None:
            pack_proof(args.proof_zipfile, args.pubkey, args.ballotbox,
                       args.shuffled)
            log.info("Stored proof in {}".format(args.proof_zipfile))
