package org.openmuc.j60870.app;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;

import org.openmuc.j60870.ASdu;
import org.openmuc.j60870.ASduType;
import org.openmuc.j60870.CauseOfTransmission;
import org.openmuc.j60870.Connection;
import org.openmuc.j60870.ConnectionEventListener;
import org.openmuc.j60870.Server;
import org.openmuc.j60870.ServerEventListener;
import org.openmuc.j60870.ie.IeQuality;
import org.openmuc.j60870.ie.IeScaledValue;
import org.openmuc.j60870.ie.IeSingleCommand;
import org.openmuc.j60870.ie.InformationElement;
import org.openmuc.j60870.ie.InformationObject;

public class SampleServer {
    public class ServerListener implements ServerEventListener {

        public class ConnectionListener implements ConnectionEventListener {

            private final Connection connection;
            private final int connectionId;
            public HashMap<Integer, Integer> valuePairs = new HashMap<>();

            public ConnectionListener(Connection connection, int connectionId) {
                this.connection = connection;
                this.connectionId = connectionId;
            }

            @Override
            public void newASdu(ASdu aSdu) {
                try {
                    InformationObject informationObject = null;
                    String data = null;
                    switch (aSdu.getTypeIdentification()) {
                        // interrogation command
                        case C_IC_NA_1:
                            connection.sendConfirmation(aSdu);
                            println("Got interrogation command. Will send scaled measured values.\n");

                            for (Integer ioa : valuePairs.keySet()) {
                                connection.send(new ASdu(ASduType.M_ME_NB_1, true, CauseOfTransmission.SPONTANEOUS, false,
                                        false, 0, aSdu.getCommonAddress(),

                                        new InformationObject(ioa, new InformationElement[][]{
                                                {new IeScaledValue(valuePairs.get(ioa)), new IeQuality(true, true, true, true, true)},
                                        })));
                            }

                            break;
                        case C_SE_NB_1:
                            informationObject = aSdu.getInformationObjects()[0];
                            data = String.valueOf(informationObject.getInformationElements()[0][0]);

                            URL url = new URL("http://localhost:5000/update");
                            HttpURLConnection con = (HttpURLConnection) url.openConnection();
                            con.setRequestMethod("POST");
                            con.setRequestProperty("Content-Type", "application/json; utf-8");
                            con.setRequestProperty("Accept", "application/json");
                            con.setDoOutput(true);
                            String jsonInputString = String.format("{\"%s\": %s}", String.valueOf(informationObject.getInformationObjectAddress()), data.split(" ")[2]);

                            valuePairs.put(informationObject.getInformationObjectAddress(), Integer.parseInt(data.split(" ")[2]));

                            try (OutputStream os = con.getOutputStream()) {
                                byte[] input = jsonInputString.getBytes("utf-8");
                                os.write(input, 0, input.length);
                            }

                            try (BufferedReader br = new BufferedReader(
                                    new InputStreamReader(con.getInputStream(), "utf-8"))) {
                                StringBuilder response = new StringBuilder();
                                String responseLine = null;
                                while ((responseLine = br.readLine()) != null) {
                                    response.append(responseLine.trim());
                                }
                            }

                            connection.sendConfirmation(aSdu);
                            println("Got set-point command, scaled value without time tag. Will write data");
                            println(Arrays.toString(aSdu.getInformationObjects()));
                            break;
                        case C_SC_NA_1:
                            informationObject = aSdu.getInformationObjects()[0];
                            connection.sendConfirmation(aSdu);
                            try {
                                BufferedReader br = new BufferedReader(new FileReader(String.valueOf(informationObject.getInformationObjectAddress())));
                                data = br.readLine();
                                connection.send(new ASdu(ASduType.M_ME_NB_1, true, CauseOfTransmission.SPONTANEOUS, false,
                                        false, 0, aSdu.getCommonAddress(),

                                        new InformationObject(informationObject.getInformationObjectAddress(), new InformationElement[][]{
                                                {new IeScaledValue(Integer.parseInt(data)), new IeQuality(true, true, true, true, true)}
                                        })));
                            } catch (FileNotFoundException e) {
                                connection.send(new ASdu(ASduType.M_ME_NB_1, true, CauseOfTransmission.SPONTANEOUS, false,
                                        false, 0, aSdu.getCommonAddress(),

                                        new InformationObject(informationObject.getInformationObjectAddress(), new InformationElement[][]{
                                                {new IeScaledValue(0), new IeQuality(true, true, true, true, true)}
                                        })));
                            }
                            break;
                        default:
                            println("Got unknown request: ", aSdu.toString(), ". Will not confirm it.\n");
                    }

                } catch (EOFException e) {
                    println("Will quit listening for commands on connection (" + connectionId,
                            ") because socket was closed.");
                } catch (IOException e) {
                    println("Will quit listening for commands on connection (" + connectionId, ") because of error: \"",
                            e.getMessage(), "\".");
                }
            }

            @Override
            public void connectionClosed(IOException e) {
                println("Connection (" + connectionId, ") was closed. ", e.getMessage());
            }

        }

        @Override
        public void connectionIndication(Connection connection) {

            int myConnectionId = connectionIdCounter++;
            println("A client has connected using TCP/IP. Will listen for a StartDT request. Connection ID: "
                    + myConnectionId);

            try {
                connection.waitForStartDT(new SampleServer.ServerListener.ConnectionListener(connection, myConnectionId), 5000);
            } catch (InterruptedIOException e) {
                // ignore: nothing to do
            } catch (IOException e) {
                println("Connection (" + myConnectionId, ") interrupted while waiting for StartDT: ", e.getMessage(),
                        ". Will quit.");
                return;
            }
            println("Started data transfer on connection (" + myConnectionId, ") Will listen for incoming commands.");

        }

        @Override
        public void serverStoppedListeningIndication(IOException e) {
            println("Server has stopped listening for new connections : \"", e.getMessage(), "\". Will quit.");
        }

        @Override
        public void connectionAttemptFailed(IOException e) {
            println("Connection attempt failed: ", e.getMessage());

        }

    }

    private int connectionIdCounter = 1;

    public static void main(String[] args) {
        new SampleServer().start();
    }

    public void start() {
        Server server = Server.builder().build();

        try {
            server.start(new SampleServer.ServerListener());
        } catch (IOException e) {
            println("Unable to start listening: \"", e.getMessage(), "\". Will quit.");
        }
    }

    private void println(String... strings) {
        StringBuilder sb = new StringBuilder();
        for (String string : strings) {
            sb.append(string);
        }
        System.out.println(sb.toString());
    }
}

