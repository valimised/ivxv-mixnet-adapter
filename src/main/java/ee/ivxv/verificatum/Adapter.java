/*

Copyright (C) 2019 State Electoral Office

This file is part of ivxv-verificatum.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License along
with this program.  If not, see <https://www.gnu.org/licenses/>.

*/

package ee.ivxv.verificatum;

import com.verificatum.arithm.ArithmFormatException;
import com.verificatum.arithm.LargeInteger;
import com.verificatum.arithm.ModPGroup;
import com.verificatum.arithm.ModPGroupElement;
import com.verificatum.arithm.PGroup;
import com.verificatum.arithm.PGroupElement;
import com.verificatum.arithm.PGroupElementArray;
import com.verificatum.arithm.PGroupElementIterator;
import com.verificatum.arithm.PPGroup;
import com.verificatum.arithm.PPGroupElement;
import com.verificatum.crypto.RandomSource;
import com.verificatum.protocol.ProtocolFormatException;
import com.verificatum.protocol.elgamal.ProtocolElGamalInterface;
import ee.ivxv.common.crypto.Plaintext;
import ee.ivxv.common.crypto.elgamal.ElGamalCiphertext;
import ee.ivxv.common.crypto.elgamal.ElGamalParameters;
import ee.ivxv.common.crypto.elgamal.ElGamalPublicKey;
import ee.ivxv.common.math.GroupElement;
import ee.ivxv.common.math.MathException;
import ee.ivxv.common.model.AnonymousBallotBox;
import ee.ivxv.common.util.Json;
import ee.ivxv.common.util.Util;
import java.io.File;
import java.io.IOException;
import java.math.BigInteger;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Adapter extends ProtocolElGamalInterface {
    private static ModPGroup getModPGroup(PGroup pgroup) {
        // get underlying Verificatum ModPGroup from the product group
        PPGroup ppgroup = (PPGroup) pgroup;
        PPGroup pppgroup = (PPGroup) ppgroup.project(0);
        ModPGroup modpgroup = (ModPGroup) pppgroup.project(0);
        return modpgroup;
    }

    private static ElGamalParameters gpV2I(ModPGroup modpgroup) throws Exception {
        // get IVXV ElGamalParameter from Verificatum ModPGroup
        LargeInteger p = modpgroup.getModulus();
        LargeInteger g = ((ModPGroupElement) modpgroup.getg()).toLargeInteger();
        ee.ivxv.common.math.ModPGroup iGroup =
                new ee.ivxv.common.math.ModPGroup(p.toBigInteger(), false);
        ee.ivxv.common.math.ModPGroupElement ig =
                new ee.ivxv.common.math.ModPGroupElement(iGroup, g.toBigInteger());
        return new ElGamalParameters(iGroup, ig);
    }

    private static ModPGroup gpI2V(ElGamalParameters param, RandomSource rnd, int certainty) {
        // get Verificatum ModPGroup from IVXV ElGamalParameters
        LargeInteger p = new LargeInteger(param.getOrder());
        LargeInteger g = new LargeInteger(
                ((ee.ivxv.common.math.ModPGroupElement) param.getGenerator()).getValue());
        LargeInteger q = new LargeInteger(param.getGeneratorOrder());
        ModPGroup modpgroup = null;
        try {
            modpgroup = new ModPGroup(p, q, g, ModPGroup.SAFEPRIME_ENCODING, rnd, certainty);
        } catch (ArithmFormatException e) {
            // our public key is correct
        }
        return modpgroup;
    }

    private static PPGroupElement ctI2V(ModPGroup modpgroup, ElGamalCiphertext ct) {
        // encode IVXV ElGamalCiphertext as Verificatum product group element
        BigInteger blind = ((ee.ivxv.common.math.ModPGroupElement) ct.getBlind()).getValue();
        BigInteger blinded =
                ((ee.ivxv.common.math.ModPGroupElement) ct.getBlindedMessage()).getValue();
        PPGroup pgroup = new PPGroup(modpgroup, modpgroup);
        PPGroupElement res =
                pgroup.product(new ModPGroupElement(modpgroup, new LargeInteger(blind)),
                        new ModPGroupElement(modpgroup, new LargeInteger(blinded)));
        return res;
    }

    private static PPGroupElement ptI2V(ModPGroup modpgroup, PPGroup ppgroup2,
            ElGamalParameters param, String msg) throws MathException {
        // encode string as Verificatum product group element with public key 1 and randomness 0
        Plaintext padded = param.getGroup().pad(new Plaintext(msg));
        GroupElement encoded = param.getGroup().encode(padded);
        BigInteger encodedBI = ((ee.ivxv.common.math.ModPGroupElement) encoded).getValue();
        PPGroupElement res = ppgroup2.product(new ModPGroupElement(modpgroup, LargeInteger.ONE),
                new ModPGroupElement(modpgroup, new LargeInteger(encodedBI)));
        return res;
    }

    private static PPGroupElement ctProductV(PPGroup ppgroup5, PPGroup ppgroup52, PPGroupElement e,
            PPGroupElement d, PPGroupElement s, PPGroupElement q, PPGroupElement c) {
        // construct wide Verificatum product group element from 5 Verificatum product group
        // elements
        PPGroupElement l = ppgroup5.product(e.project(0), d.project(0), s.project(0), q.project(0),
                c.project(0));
        PPGroupElement r = ppgroup5.product(e.project(1), d.project(1), s.project(1), q.project(1),
                c.project(1));
        return ppgroup52.product(l, r);
    }

    @Override
    public void decodePlaintexts(PGroupElementArray plaintexts, File file) {
        // not implemented
    }

    @Override
    public PGroupElementArray readCiphertexts(PGroup pgroup, File file)
            throws ProtocolFormatException {
        // as we encode the district, station and question information, then the key width has to be
        // 5!
        AnonymousBallotBox abb;
        ArrayList<PGroupElement> cts = new ArrayList<PGroupElement>();
        ElGamalParameters param;
        ModPGroup modpgroup = getModPGroup(pgroup);
        PPGroup ppgroup5 = new PPGroup(modpgroup, 5);
        PPGroup ppgroup52 = new PPGroup(ppgroup5, 2);
        PPGroup ppgroup2 = new PPGroup(modpgroup, 2);
        try {
            param = gpV2I(modpgroup);
        } catch (Exception e) {
            throw new ProtocolFormatException("Exception while constructing group", e);
        }
        try {
            abb = Json.read(file.toPath(), AnonymousBallotBox.class);
        } catch (Exception e) {
            throw new ProtocolFormatException("Exception while parsing anonymous ballot box", e);
        }
        PPGroupElement electionPP;
        try {
            electionPP = ptI2V(modpgroup, ppgroup2, param, abb.getElection());
        } catch (MathException e) {
            throw new RuntimeException(e);
        }
        abb.getDistricts().forEach((district, sMap) -> {
            PPGroupElement districtPP;
            try {
                districtPP = ptI2V(modpgroup, ppgroup2, param, district);
            } catch (MathException e) {
                throw new RuntimeException(e);
            }
            sMap.forEach((station, qMap) -> {
                PPGroupElement stationPP;
                try {
                    stationPP = ptI2V(modpgroup, ppgroup2, param, station);
                } catch (MathException e) {
                    throw new RuntimeException(e);
                }
                qMap.forEach((question, cList) -> {
                    PPGroupElement questionPP;
                    try {
                        questionPP = ptI2V(modpgroup, ppgroup2, param, question);
                    } catch (MathException e) {
                        throw new RuntimeException(e);
                    }
                    cList.forEach(ctb -> {
                        ElGamalCiphertext ct = new ElGamalCiphertext(param, ctb);
                        PPGroupElement ctPP = ctI2V(modpgroup, ct);
                        PPGroupElement res = ctProductV(ppgroup5, ppgroup52, electionPP, districtPP,
                                stationPP, questionPP, ctPP);
                        cts.add(res);
                    });
                });
            });
        });
        return pgroup.toElementArray(cts.toArray(new PPGroupElement[0]));
    }

    @Override
    public PGroupElement readPublicKey(File file, RandomSource rnd, int certainty)
            throws ProtocolFormatException {
        String keyString = null;
        try {
            keyString = new String(Files.readAllBytes(file.toPath()), Util.CHARSET);
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        ElGamalPublicKey pub = new ElGamalPublicKey(Util.decodePublicKey(keyString));
        BigInteger y = ((ee.ivxv.common.math.ModPGroupElement) pub.getKey()).getValue();
        ModPGroup modpgroup = gpI2V(pub.getParameters(), rnd, certainty);
        PPGroup ppgroup5 = new PPGroup(modpgroup, 5);
        PPGroup ppgroup52 = new PPGroup(ppgroup5, 2);
        ModPGroupElement g = (ModPGroupElement) modpgroup.getg();
        ModPGroupElement py = new ModPGroupElement(modpgroup, LargeInteger.ONE);
        PPGroupElement G = ppgroup5.product(g, g, g, g, g);
        PPGroupElement Y = ppgroup5.product(py, py, py, py,
                new ModPGroupElement(modpgroup, new LargeInteger(y)));
        PPGroupElement key = ppgroup52.product(G, Y);
        return key;
    }

    @Override
    public void writeCiphertexts(PGroupElementArray ciphertexts, File file) {
        PGroup pgroup = ciphertexts.getPGroup();
        ModPGroup modpgroup = getModPGroup(pgroup);
        ElGamalParameters param;
        Map<String, Map<String, Map<String, List<byte[]>>>> res =
                new LinkedHashMap<String, Map<String, Map<String, List<byte[]>>>>();
        try {
            param = gpV2I(modpgroup);
        } catch (Exception e1) {
            return;
        }
        String election = null;
        PGroupElementIterator it = ciphertexts.getIterator();
        while (it.hasNext()) {
            PGroupElement el = it.next();
            String thiselection = ppgeV2I(param, el, 0);
            String district = ppgeV2I(param, el, 1);
            String station = ppgeV2I(param, el, 2);
            String question = ppgeV2I(param, el, 3);
            ElGamalCiphertext cc = parseCtPos(param, el, 4);
            if (election == null) {
                election = thiselection;
            }
            if (!election.equals(thiselection)) {
                throw new RuntimeException("Invalid election");
            }
            res.computeIfAbsent(district, x -> new LinkedHashMap<>())
                    .computeIfAbsent(station, x -> new LinkedHashMap<>())
                    .computeIfAbsent(question, x -> new ArrayList<byte[]>()).add(cc.getBytes());
        }
        AnonymousBallotBox abb = new AnonymousBallotBox(election, res);
        try {
            Json.write(abb, file.toPath());
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static String ppgeV2I(ElGamalParameters param, PGroupElement el, int pos) {
        // convert dummy Verificatum ciphertext to IVXV Plaintext (decoded as UTF8)
        PPGroupElement r = (PPGroupElement) ((PPGroupElement) el).project(1);
        ModPGroupElement rposval = (ModPGroupElement) r.project(pos);
        ee.ivxv.common.math.ModPGroup iGroup = ((ee.ivxv.common.math.ModPGroup) param.getGroup());
        ee.ivxv.common.math.ModPGroupElement encoded = new ee.ivxv.common.math.ModPGroupElement(
                iGroup, rposval.toLargeInteger().toBigInteger());
        Plaintext padded = iGroup.decode(encoded);
        Plaintext pt = padded.stripPadding();
        String msg = pt.getUTF8DecodedMessage();
        return msg;
    }

    private static ElGamalCiphertext parseCtPos(ElGamalParameters param, PGroupElement el,
            int pos) {
        // convert Verificatum ciphertext (product group element) to IVXV ElGamalCiphertext
        PPGroupElement l = (PPGroupElement) ((PPGroupElement) el).project(0);
        PPGroupElement r = (PPGroupElement) ((PPGroupElement) el).project(1);
        ModPGroupElement lposval = (ModPGroupElement) l.project(pos);
        ModPGroupElement rposval = (ModPGroupElement) r.project(pos);
        ee.ivxv.common.math.ModPGroup iGroup = ((ee.ivxv.common.math.ModPGroup) param.getGroup());
        ee.ivxv.common.math.ModPGroupElement ilposval = new ee.ivxv.common.math.ModPGroupElement(
                iGroup, lposval.toLargeInteger().toBigInteger());
        ee.ivxv.common.math.ModPGroupElement irposval = new ee.ivxv.common.math.ModPGroupElement(
                iGroup, rposval.toLargeInteger().toBigInteger());
        ElGamalCiphertext c = new ElGamalCiphertext(ilposval, irposval, param.getOID());
        return c;
    }

    @Override
    public void writePublicKey(PGroupElement fullPublicKey, File file) {
        // not implemented
    }
}
