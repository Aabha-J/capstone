// Capstone FPGA baseline: two logical chiplets on one DE1-SoC.
// KEY[0] resets, KEY[1] starts/stops, SW[3:0] sets the send interval.
// LEDR[0] running, LEDR[1] last packet received, LEDR[2] error.
// LEDR[9:3] shows the lower seven bits of last measured latency.
module de1_soc_top (
    input wire CLOCK_50,
    input wire [3:0] KEY,
    input wire [9:0] SW,
    output wire [9:0] LEDR
);
    // Buttons are active low. Synchronize the start button to the FPGA clock.
    reg [1:0] key_sync;
    reg key_previous;
    reg running;
    wire reset_n = KEY[0];
    always @(posedge CLOCK_50 or negedge reset_n) begin
        if (!reset_n) begin
            key_sync <= 2'b11;
            key_previous <= 1'b1;
            running <= 1'b0;
        end else begin
            key_sync <= {key_sync[0], KEY[1]};
            key_previous <= key_sync[1];
            if (key_previous && !key_sync[1]) running <= !running;
        end
    end

    reg [31:0] cycle_counter;
    reg [31:0] sent_at;
    reg [31:0] latency_cycles;
    reg [31:0] packets_sent;
    reg [31:0] packets_received;
    reg [31:0] errors;
    reg [31:0] interval_counter;
    reg [15:0] sequence;
    reg received_toggle;
    reg tx_valid;
    reg [15:0] tx_data;
    wire tx_ready, rx_valid;
    wire [15:0] rx_data;
    wire [31:0] send_interval = 32'd100 + ({28'd0, SW[3:0]} * 32'd100);

    chiplet_link #(.DATA_W(16), .LINK_CYCLES(2)) link0 (
        .clk(CLOCK_50), .reset_n(reset_n),
        .tx_valid(tx_valid), .tx_data(tx_data), .tx_ready(tx_ready),
        .rx_valid(rx_valid), .rx_data(rx_data), .rx_ready(1'b1)
    );

    // Keep the traffic and measurements in the same clock domain.
    // A transfer happens only when valid and ready are both high.
    always @(posedge CLOCK_50 or negedge reset_n) begin
        if (!reset_n) begin
            cycle_counter <= 0;
            sent_at <= 0;
            latency_cycles <= 0;
            packets_sent <= 0;
            packets_received <= 0;
            errors <= 0;
            interval_counter <= 0;
            sequence <= 0;
            received_toggle <= 0;
            tx_valid <= 0;
            tx_data <= 0;
        end else begin
            cycle_counter <= cycle_counter + 1'b1;
            if (interval_counter < send_interval)
                interval_counter <= interval_counter + 1'b1;

            // Prepare the next packet when the link is free.
            if (!tx_valid && running && tx_ready && interval_counter >= send_interval) begin
                tx_data <= sequence;
                tx_valid <= 1'b1;
            end

            if (tx_valid && tx_ready) begin
                tx_valid <= 1'b0;
                sent_at <= cycle_counter;
                packets_sent <= packets_sent + 1'b1;
                sequence <= sequence + 1'b1;
                interval_counter <= 0;
            end

            if (rx_valid) begin
                packets_received <= packets_received + 1'b1;
                latency_cycles <= cycle_counter - sent_at;
                received_toggle <= !received_toggle;
                if (rx_data != (sequence - 16'd1))
                    errors <= errors + 1'b1;
            end
        end
    end

    assign LEDR[0] = running;
    assign LEDR[1] = received_toggle;
    assign LEDR[2] = (errors != 0);
    assign LEDR[9:3] = latency_cycles[6:0];
endmodule
