`timescale 1ns/1ps
// Basic link test. Send two packets and check that neither is lost.
module tb_chiplet_link;
  reg clk = 0;
  always #10 clk = ~clk; // 50 MHz
  reg reset_n = 0;
  reg tx_valid = 0;
  reg [15:0] tx_data = 0;
  wire tx_ready, rx_valid;
  wire [15:0] rx_data;
  reg rx_ready = 1;
  integer received = 0;
  chiplet_link #(.DATA_W(16), .LINK_CYCLES(2)) dut (
    .clk(clk), .reset_n(reset_n), .tx_valid(tx_valid),
    .tx_data(tx_data), .tx_ready(tx_ready),
    .rx_valid(rx_valid), .rx_data(rx_data), .rx_ready(rx_ready)
  );
  always @(posedge clk) if (reset_n && rx_valid && rx_ready) begin
    if (rx_data !== (received + 16'h1234)) $fatal(1, "Unexpected packet %h", rx_data);
    received = received + 1;
  end
  task send(input [15:0] value);
    begin
      @(negedge clk);
      while (!tx_ready) @(negedge clk);
      tx_data = value;
      tx_valid = 1;
      @(negedge clk);
      tx_valid = 0;
    end
  endtask
  initial begin
    repeat (3) @(negedge clk);
    reset_n = 1;
    send(16'h1234);
    send(16'h1235);
    repeat (12) @(negedge clk);
    if (received != 2) $fatal(1, "Expected 2 packets, got %0d", received);
    $display("PASS: both packets received correctly");
    $finish;
  end
endmodule
