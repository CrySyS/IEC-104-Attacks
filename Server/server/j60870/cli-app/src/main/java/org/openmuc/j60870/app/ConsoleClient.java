/*
 * Copyright 2014-19 Fraunhofer ISE
 *
 * This file is part of j60870.
 * For more information visit http://www.openmuc.org
 *
 * j60870 is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * j60870 is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with j60870.  If not, see <http://www.gnu.org/licenses/>.
 *
 */
package org.openmuc.j60870.app;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.URL;
import java.net.UnknownHostException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

import org.openmuc.j60870.ASdu;
import org.openmuc.j60870.CauseOfTransmission;
import org.openmuc.j60870.ClientConnectionBuilder;
import org.openmuc.j60870.Connection;
import org.openmuc.j60870.ConnectionEventListener;
import org.openmuc.j60870.ie.*;
import org.openmuc.j60870.internal.cli.Action;
import org.openmuc.j60870.internal.cli.ActionException;
import org.openmuc.j60870.internal.cli.ActionListener;
import org.openmuc.j60870.internal.cli.ActionProcessor;
import org.openmuc.j60870.internal.cli.CliParameter;
import org.openmuc.j60870.internal.cli.CliParameterBuilder;
import org.openmuc.j60870.internal.cli.CliParseException;
import org.openmuc.j60870.internal.cli.CliParser;
import org.openmuc.j60870.internal.cli.IntCliParameter;
import org.openmuc.j60870.internal.cli.StringCliParameter;

public final class ConsoleClient {

    private static final String INTERROGATION_ACTION_KEY = "i";
    private static final String CLOCK_SYNC_ACTION_KEY = "c";
    private static final String SINGLE_COMMAND_SELECT = "s";
    private static final String SINGLE_COMMAND_EXECUTE = "e";
    private static final String SET_POINT_COMMAND = "p";
    private static final String GET_POINT_SCALED = "g";
    private static HashMap<String, Integer> stationToIOA = new HashMap<>();

    private static final StringCliParameter hostParam = new CliParameterBuilder("-h")
            .setDescription("The IP/domain address of the server you want to access.")
            .setMandatory()
            .buildStringParameter("host");
    private static final IntCliParameter portParam = new CliParameterBuilder("-p")
            .setDescription("The port to connect to.")
            .buildIntParameter("port", 2404);
    private static final IntCliParameter commonAddrParam = new CliParameterBuilder("-ca")
            .setDescription("The address of the target station or the broad cast address.")
            .buildIntParameter("common_address", 1);
    private static final IntCliParameter startDtTimeout = new CliParameterBuilder("-t")
            .setDescription("Start DT timeout. For deactivating with set 0.")
            .buildIntParameter("start_DT_timeout", 5000);
    private static final IntCliParameter startDtRetries = new CliParameterBuilder("-r")
            .setDescription("Send start DT retries.")
            .buildIntParameter("start_DT_retries", 1);
    private static final IntCliParameter messageFragmentTimeout = new CliParameterBuilder("-mft")
            .setDescription("Message fragment timeout.")
            .buildIntParameter("message_fragment_timeout", 5000);

    private static Connection connection;
    private static final ActionProcessor actionProcessor = new ActionProcessor(new ActionExecutor());

    private static class ClientEventListener implements ConnectionEventListener {

        @Override
        public void newASdu(ASdu aSdu) {
            try {
                println("\nReceived ASDU:\n", aSdu.toString());
                for (InformationObject i : aSdu.getInformationObjects()) {
                    String data = i.getInformationElements()[0][0].toString();

                    URL url = new URL("http://localhost:5000/update");
                    HttpURLConnection con = (HttpURLConnection) url.openConnection();
                    con.setRequestMethod("POST");
                    con.setRequestProperty("Content-Type", "application/json; utf-8");
                    con.setRequestProperty("Accept", "application/json");
                    con.setDoOutput(true);
                    String jsonInputString = String.format("{\"%s\": %s}", String.valueOf(i.getInformationObjectAddress()), data.split(" ")[2]);

                    try(OutputStream os = con.getOutputStream()) {
                        byte[] input = jsonInputString.getBytes("utf-8");
                        os.write(input, 0, input.length);
                    }

                    try(BufferedReader br = new BufferedReader(
                            new InputStreamReader(con.getInputStream(), "utf-8"))) {
                        StringBuilder response = new StringBuilder();
                        String responseLine = null;
                        while ((responseLine = br.readLine()) != null) {
                            response.append(responseLine.trim());
                        }
                    }

                    println((i.getInformationElements())[0][0].toString());
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        @Override
        public void connectionClosed(IOException e) {
            println("Received connection closed signal. Reason: ");
            if (!e.getMessage().isEmpty()) {
                println(e.getMessage());
            } else {
                println("unknown");
            }
            actionProcessor.close();
        }

    }

    private static class ActionExecutor implements ActionListener {
        @Override
        public void actionCalled(String actionKey) throws ActionException {
            try {
                BufferedReader reader =
                        new BufferedReader(new InputStreamReader(System.in));
                switch (actionKey) {
                    case INTERROGATION_ACTION_KEY:
                        println("** Sending general interrogation command.");
                        connection.interrogation(commonAddrParam.getValue(), CauseOfTransmission.ACTIVATION,
                                new IeQualifierOfInterrogation(20));
                        break;
                    case CLOCK_SYNC_ACTION_KEY:
                        println("** Sending synchronize clocks command.");
                        connection.synchronizeClocks(commonAddrParam.getValue(), new IeTime56(System.currentTimeMillis()));
                        break;
                    case SINGLE_COMMAND_SELECT:
                        println("** Sending single command select.");
                        connection.singleCommand(commonAddrParam.getValue(), CauseOfTransmission.ACTIVATION, stationToIOA.get(reader.readLine()),
                                new IeSingleCommand(true, 0, true));
                        break;
                    case SET_POINT_COMMAND:
                        println("** Sending set-point command");
                        connection.setScaledValueCommand(commonAddrParam.getValue(), CauseOfTransmission.ACTIVATION, stationToIOA.get(reader.readLine()), new IeScaledValue(Integer.parseInt(reader.readLine())), new IeQualifierOfSetPointCommand(0, false));
                    case GET_POINT_SCALED:
                        break;
                    default:
                        break;
                }
            } catch (Exception e) {
                throw new ActionException(e);
            }
        }

        @Override
        public void quit() {
            println("** Closing connection.");
            connection.close();
        }
    }

    public static void setDefaultValues() {
        try {
            BufferedReader br = new BufferedReader(new FileReader("binding.json"));
            String line = br.readLine();
            StringBuilder dataBuilder = new StringBuilder();
            while (line != null) {
                dataBuilder.append(line);
                line = br.readLine();
            }
            String data = dataBuilder.toString();
            data = data.trim();
            data = data.replace("{", "");
            data = data.replace("}", "");
            data = data.replace("\n", "");
            data = data.replace(" ", "");
            data = data.replace("\"", "");
            String[] elements = data.split(",");
            for (String e : elements) {
                String name = e.split(":")[0];
                Integer value = Integer.parseInt(e.split(":")[1]);
                stationToIOA.put(name, value);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        try {
            BufferedReader br = new BufferedReader(new FileReader("consumption.csv"));
            String line = br.readLine();
            StringBuilder dataBuilder = new StringBuilder();
            while (line != null) {
                dataBuilder.append(line + "\n");
                line = br.readLine();
            }
            String data = dataBuilder.toString();
            String[] lines = data.split("\n");
            HashMap<Integer, String> stations = new HashMap<>();
            stations.put(0, "S");
            stations.put(1, "A");
            stations.put(2, "B");
            stations.put(3, "C");
            stations.put(4, "E");
            stations.put(5, "F");
            stations.put(6, "G");
            stations.put(7, "H");
            stations.put(8, "I");
            stations.put(9, "J");
            stations.put(10, "K");
            stations.put(11, "L");
            stations.put(12, "D");

            int iter = 0;
//            while (true) {
//                if (iter >= lines[0].split(",").length)
//                    iter = 0;
//                System.out.println(iter);
//
//                for (int i = 0; i < lines.length; i++) {
//                    int ioa = stationToIOA.get(stations.get(i));
//                    int value = (int) Double.parseDouble(lines[i].split(",")[iter]) / 10;
//                    connection.setScaledValueCommand(commonAddrParam.getValue(), CauseOfTransmission.ACTIVATION, ioa, new IeScaledValue(value), new IeQualifierOfSetPointCommand(0, false));
//                    Thread.sleep(1000);
//                }
//                iter++;
//
//                Thread.sleep(30000);
//            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) {
        List<CliParameter> cliParameters = new ArrayList<>();
        cliParameters.add(hostParam);
        cliParameters.add(portParam);
        cliParameters.add(commonAddrParam);

        CliParser cliParser = new CliParser("j60870-console-client",
                "A client/master application to access IEC 60870-5-104 servers/slaves.");
        cliParser.addParameters(cliParameters);

        try {
            cliParser.parseArguments(args);
        } catch (CliParseException e1) {
            System.err.println("Error parsing command line parameters: " + e1.getMessage());
            println(cliParser.getUsageString());
            System.exit(1);
        }

        InetAddress address;
        try {
            address = InetAddress.getByName(hostParam.getValue());
        } catch (UnknownHostException e) {
            println("Unknown host: ", hostParam.getValue());
            return;
        }

        ClientConnectionBuilder clientConnectionBuilder = new ClientConnectionBuilder(address)
                .setMessageFragmentTimeout(messageFragmentTimeout.getValue())
                .setPort(portParam.getValue());

        try {
            connection = clientConnectionBuilder.build();
        } catch (IOException e) {
            println("Unable to connect to remote host: ", hostParam.getValue(), ".");
            return;
        }

        Runtime.getRuntime().addShutdownHook(new Thread() {
            @Override
            public void run() {
                connection.close();
            }
        });

        boolean connected = false;
        int retries = startDtRetries.getValue();
        int i = 1;

        while (!connected && i <= retries) {
            try {
                println("Send start DT. Try no. " + i);
                connection.startDataTransfer(new ClientEventListener(), startDtTimeout.getValue());
            } catch (InterruptedIOException e2) {
                if (i == retries) {
                    println("Starting data transfer timed out. Closing connection. Because of no more retries.");
                    connection.close();
                    return;
                } else {
                    println("Got Timeout.class Next try.");
                    ++i;
                    continue;
                }
            } catch (IOException e) {
                println("Connection closed for the following reason: ", e.getMessage());
                return;
            }

            connected = true;
        }
        println("successfully connected");
        setDefaultValues();
        actionProcessor.addAction(new Action(INTERROGATION_ACTION_KEY, "interrogation C_IC_NA_1"));
        actionProcessor.addAction(new Action(CLOCK_SYNC_ACTION_KEY, "synchronize clocks C_CS_NA_1"));
        actionProcessor.addAction(new Action(SINGLE_COMMAND_SELECT, "single command select C_SC_NA_1"));
        actionProcessor.addAction(new Action(SINGLE_COMMAND_EXECUTE, "single command execute C_SC_NA_1"));
        actionProcessor.addAction(new Action(SET_POINT_COMMAND, "set-point command C_SE_NB_1"));

        actionProcessor.start();
    }

    private static void println(String... strings) {
        StringBuilder sb = new StringBuilder();
        for (String string : strings) {
            sb.append(string);
        }
        System.out.println(sb.toString());
    }

}

